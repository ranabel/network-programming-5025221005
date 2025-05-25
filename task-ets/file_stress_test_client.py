import socket
import json
import base64
import logging
import os
import time
import random
import concurrent.futures
import argparse
import statistics
import csv
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(message)s',
    handlers=[
        logging.FileHandler("performance_test.log"),
        logging.StreamHandler()
    ]
)

class PerformanceTester:
    def __init__(self, server_addr=('localhost', 6667)):
        self.server = server_addr
        self.test_results = {
            'upload': {'success': 0, 'fail': 0, 'data': []},
            'download': {'success': 0, 'fail': 0, 'data': []},
            'list': {'success': 0, 'fail': 0, 'data': []}
        }
        
        os.makedirs('test_data', exist_ok=True)
        os.makedirs('downloads', exist_ok=True)

    def create_test_file(self, size_mb):
        filename = f"test_{size_mb}mb.dat"
        filepath = os.path.join('test_data', filename)
        
        if os.path.exists(filepath) and os.path.getsize(filepath) == size_mb * 1024 * 1024:
            return filepath
            
        logging.info(f"Creating {size_mb}MB test file")
        chunk = 1024 * 1024
        with open(filepath, 'wb') as f:
            for _ in range(size_mb):
                f.write(os.urandom(chunk))
        return filepath

    def send_request(self, request):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(300)
        try:
            sock.connect(self.server)
            
            chunks = [request[i:i+65536] for i in range(0, len(request), 65536)]
            for chunk in chunks:
                sock.sendall(chunk.encode())
            sock.sendall("\r\n\r\n".encode())
            
            response = ""
            while True:
                data = sock.recv(1024*1024)
                if not data:
                    break
                response += data.decode()
                if "\r\n\r\n" in response:
                    break
            
            return json.loads(response.split("\r\n\r\n")[0])
        except Exception as e:
            return {'status': 'ERROR', 'error': str(e)}
        finally:
            sock.close()

    def test_upload(self, file_path, worker_id):
        start = time.time()
        filename = os.path.basename(file_path)
        size = os.path.getsize(file_path)
        
        try:
            with open(file_path, 'rb') as f:
                encoded = base64.b64encode(f.read()).decode()
            
            cmd = f"upload {filename} {encoded}"
            result = self.send_request(cmd)
            
            duration = time.time() - start
            speed = size / duration if duration > 0 else 0
            
            if result['status'] == 'SUCCESS':
                logging.info(f"Worker {worker_id}: Uploaded {filename} ({size/1024/1024:.1f}MB) in {duration:.2f}s ({speed/1024/1024:.1f}MB/s)")
                self.test_results['upload']['success'] += 1
            else:
                logging.error(f"Worker {worker_id}: Upload failed: {result.get('error', 'Unknown error')}")
                self.test_results['upload']['fail'] += 1
                
            return {
                'worker': worker_id,
                'operation': 'upload',
                'size': size,
                'time': duration,
                'speed': speed,
                'status': result['status']
            }
        except Exception as e:
            duration = time.time() - start
            logging.error(f"Worker {worker_id}: Upload exception: {str(e)}")
            self.test_results['upload']['fail'] += 1
            return {
                'worker': worker_id,
                'operation': 'upload',
                'size': size,
                'time': duration,
                'speed': 0,
                'status': 'ERROR',
                'error': str(e)
            }

    def test_download(self, filename, worker_id):
        start = time.time()
        
        try:
            cmd = f"get {filename}"
            result = self.send_request(cmd)
            
            if result['status'] == 'SUCCESS':
                content = base64.b64decode(result['content'])
                size = len(content)
                
                dl_path = os.path.join('downloads', f"{worker_id}_{filename}")
                with open(dl_path, 'wb') as f:
                    f.write(content)
                
                duration = time.time() - start
                speed = size / duration if duration > 0 else 0
                
                logging.info(f"Worker {worker_id}: Downloaded {filename} ({size/1024/1024:.1f}MB) in {duration:.2f}s ({speed/1024/1024:.1f}MB/s)")
                self.test_results['download']['success'] += 1
                
                return {
                    'worker': worker_id,
                    'operation': 'download',
                    'size': size,
                    'time': duration,
                    'speed': speed,
                    'status': 'SUCCESS'
                }
            else:
                duration = time.time() - start
                logging.error(f"Worker {worker_id}: Download failed: {result.get('error', 'Unknown error')}")
                self.test_results['download']['fail'] += 1
                return {
                    'worker': worker_id,
                    'operation': 'download',
                    'size': 0,
                    'time': duration,
                    'speed': 0,
                    'status': 'ERROR',
                    'error': result.get('error', 'Unknown error')
                }
        except Exception as e:
            duration = time.time() - start
            logging.error(f"Worker {worker_id}: Download exception: {str(e)}")
            self.test_results['download']['fail'] += 1
            return {
                'worker': worker_id,
                'operation': 'download',
                'size': 0,
                'time': duration,
                'speed': 0,
                'status': 'ERROR',
                'error': str(e)
            }

    def test_list(self, worker_id):
        start = time.time()
        
        try:
            result = self.send_request("list")
            duration = time.time() - start
            
            if result['status'] == 'SUCCESS':
                count = len(result.get('files', []))
                logging.info(f"Worker {worker_id}: Listed {count} files in {duration:.2f}s")
                self.test_results['list']['success'] += 1
            else:
                logging.error(f"Worker {worker_id}: List failed: {result.get('error', 'Unknown error')}")
                self.test_results['list']['fail'] += 1
                
            return {
                'worker': worker_id,
                'operation': 'list',
                'time': duration,
                'status': result['status']
            }
        except Exception as e:
            duration = time.time() - start
            logging.error(f"Worker {worker_id}: List exception: {str(e)}")
            self.test_results['list']['fail'] += 1
            return {
                'worker': worker_id,
                'operation': 'list',
                'time': duration,
                'status': 'ERROR',
                'error': str(e)
            }

    def execute_test(self, test_type, file_size, workers, executor_type='thread'):
        self.test_results = {
            'upload': {'success': 0, 'fail': 0, 'data': []},
            'download': {'success': 0, 'fail': 0, 'data': []},
            'list': {'success': 0, 'fail': 0, 'data': []}
        }
        
        test_file = None
        if test_type in ['upload', 'download']:
            test_file = self.create_test_file(file_size)
        
        if test_type == 'download':
            upload_result = self.test_upload(test_file, 0)
            if upload_result['status'] != 'SUCCESS':
                return None
        
        executor = concurrent.futures.ThreadPoolExecutor if executor_type == 'thread' else concurrent.futures.ProcessPoolExecutor
        
        results = []
        with executor(max_workers=workers) as pool:
            tasks = []
            
            for i in range(workers):
                if test_type == 'upload':
                    tasks.append(pool.submit(self.test_upload, test_file, i))
                elif test_type == 'download':
                    tasks.append(pool.submit(self.test_download, os.path.basename(test_file), i))
                else:
                    tasks.append(pool.submit(self.test_list, i))
            
            for task in concurrent.futures.as_completed(tasks):
                try:
                    result = task.result()
                    results.append(result)
                    self.test_results[test_type]['data'].append(result)
                except Exception as e:
                    logging.error(f"Task failed: {e}")
        
        successful = [r for r in results if r['status'] == 'SUCCESS']
        failed = [r for r in results if r['status'] != 'SUCCESS']
        
        self.test_results[test_type]['success'] = len(successful)
        self.test_results[test_type]['fail'] = len(failed)
        
        if not successful:
            return {
                'test': test_type,
                'file_size': file_size,
                'workers': workers,
                'executor': executor_type,
                'success': len(successful),
                'failed': len(failed)
            }
        
        times = [r['time'] for r in successful]
        speeds = [r.get('speed', 0) for r in successful if r.get('speed', 0) > 0]
        
        stats = {
            'test': test_type,
            'file_size': file_size,
            'workers': workers,
            'executor': executor_type,
            'avg_time': statistics.mean(times),
            'median_time': statistics.median(times),
            'min_time': min(times),
            'max_time': max(times),
            'avg_speed': statistics.mean(speeds) if speeds else 0,
            'median_speed': statistics.median(speeds) if speeds else 0,
            'min_speed': min(speeds) if speeds else 0,
            'max_speed': max(speeds) if speeds else 0,
            'success': len(successful),
            'failed': len(failed)
        }
        
        logging.info(f"Test completed: {stats['success']} passed, {stats['failed']} failed")
        logging.info(f"Average time: {stats['avg_time']:.2f}s, Speed: {stats['avg_speed']/1024/1024:.1f}MB/s")
        
        return stats

    def save_report(self, all_stats):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = f"performance_report_{timestamp}.csv"
        
        with open(report_file, 'w', newline='') as f:
            fields = [
                'test', 'file_size', 'workers', 'executor',
                'avg_time', 'median_time', 'min_time', 'max_time',
                'avg_speed', 'median_speed', 'min_speed', 'max_speed',
                'success', 'failed'
            ]
            writer = csv.DictWriter(f, fieldnames=fields)
            writer.writeheader()
            writer.writerows(all_stats)
        
        logging.info(f"Report saved to {report_file}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='File Server Performance Tester')
    parser.add_argument('--host', default='localhost', help='Server hostname')
    parser.add_argument('--port', type=int, default=6667, help='Server port')
    parser.add_argument('--test', choices=['upload', 'download', 'list', 'all'], default='all', help='Test type')
    parser.add_argument('--sizes', type=int, nargs='+', default=[10, 50, 100], help='File sizes in MB')
    parser.add_argument('--clients', type=int, nargs='+', default=[1, 5, 10], help='Client counts')
    parser.add_argument('--executor', choices=['thread', 'process'], default='thread', help='Executor type')
    parser.add_argument('--debug', action='store_true', help='Enable debug logging')
    
    args = parser.parse_args()
    
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
    
    tester = PerformanceTester((args.host, args.port))
    
    if args.test == 'all':
        tests = ['upload', 'download', 'list']
    else:
        tests = [args.test]
    
    all_results = []
    for size in args.sizes:
        for clients in args.clients:
            for test in tests:
                result = tester.execute_test(test, size, clients, args.executor)
                if result:
                    all_results.append(result)
    
    tester.save_report(all_results)