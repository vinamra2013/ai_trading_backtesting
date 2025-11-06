#!/usr/bin/env python3
"""
Simple test to verify ProcessPoolExecutor works
"""
from concurrent.futures import ProcessPoolExecutor
import time

def dummy_task(task_id):
    """A dummy task that simulates work"""
    time.sleep(0.1)  # Simulate some work
    return f"Task {task_id} completed"

def main():
    print("🧪 Testing ProcessPoolExecutor")
    print("=" * 30)

    # Create some dummy tasks
    tasks = list(range(10))

    start_time = time.time()

    # Run tasks in parallel
    results = []
    with ProcessPoolExecutor(max_workers=4) as executor:
        futures = [executor.submit(dummy_task, task_id) for task_id in tasks]

        for future in futures:
            result = future.result()
            results.append(result)
            print(f"✅ {result}")

    end_time = time.time()
    duration = end_time - start_time

    print("\n📈 Results Summary:")
    print(f"   Tasks completed: {len(results)}")
    print(f"   Execution time: {duration:.2f}s")
    print("🎉 ProcessPoolExecutor test completed successfully!")

if __name__ == "__main__":
    main()