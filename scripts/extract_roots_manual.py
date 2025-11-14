"""Manually run root extraction for all existing tokens."""
import asyncio
import sys
from pathlib import Path

import httpx

API_BASE_URL = "http://localhost:8000"


async def extract_roots_for_existing_tokens():
    """Extract roots for all tokens that are missing them."""
    print("=" * 70)
    print("  Manual Root Extraction for Existing Tokens")
    print("=" * 70)
    print()
    
    # Get current stats
    async with httpx.AsyncClient() as client:
        print("[1/3] Checking current database status...")
        response = await client.get(f"{API_BASE_URL}/quran/stats")
        if response.status_code == 200:
            stats = response.json()
            print(f"  Total tokens: {stats['total_tokens']}")
            print(f"  Total roots: {stats['total_roots']}")
            
            if stats['total_roots'] > 0:
                print(f"\n  ℹ️  Some tokens already have roots.")
                response = input("  Continue anyway? (yes/no): ")
                if response.lower() not in ['yes', 'y']:
                    print("Cancelled.")
                    return
        print()
        
        # Extract roots for available suras
        print("[2/3] Starting root extraction...")
        print()
        
        suras_to_process = [1, 2]  # Based on available data
        
        for sura in suras_to_process:
            print(f"  Processing Sura {sura}...")
            
            try:
                response = await client.post(
                    f"{API_BASE_URL}/pipeline/extract-roots",
                    params={"sura": sura},
                    timeout=120
                )
                
                if response.status_code in [200, 202]:
                    data = response.json()
                    job_id = data.get("job_id")
                    print(f"    ✓ Job queued: {job_id}")
                    
                    # Wait a bit for processing
                    await asyncio.sleep(5)
                    
                    # Check job status
                    status_response = await client.get(
                        f"{API_BASE_URL}/pipeline/job/{job_id}",
                        timeout=10
                    )
                    
                    if status_response.status_code == 200:
                        job_data = status_response.json()
                        print(f"    Status: {job_data.get('status')}")
                        if job_data.get('progress'):
                            print(f"    Progress: {job_data['progress']}%")
                else:
                    print(f"    ✗ Error: HTTP {response.status_code}")
                    print(f"      {response.text[:200]}")
            
            except Exception as e:
                print(f"    ✗ Error: {e}")
            
            print()
        
        # Wait for processing to complete
        print("  Waiting 10 seconds for processing...")
        await asyncio.sleep(10)
        
        # Get final stats
        print("[3/3] Final statistics...")
        response = await client.get(f"{API_BASE_URL}/quran/stats")
        if response.status_code == 200:
            stats = response.json()
            print(f"  Total tokens: {stats['total_tokens']}")
            print(f"  Total roots: {stats['total_roots']}")
            
            if stats['total_roots'] > 0:
                coverage = (stats['total_roots'] / stats['total_tokens']) * 100
                print(f"  Coverage: {coverage:.1f}%")
            else:
                print("  ⚠️  No roots extracted yet.")
                print("  Check Celery worker logs for errors.")
    
    print()
    print("=" * 70)
    print("Complete!")
    print()
    print("View results at:")
    print(f"  {API_BASE_URL}/demo-enhanced")
    print()


if __name__ == "__main__":
    try:
        asyncio.run(extract_roots_for_existing_tokens())
    except KeyboardInterrupt:
        print("\n\nInterrupted by user.")
    except Exception as e:
        print(f"\n\nError: {e}")
        import traceback
        traceback.print_exc()
