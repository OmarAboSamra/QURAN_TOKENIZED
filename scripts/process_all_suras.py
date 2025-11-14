"""Process all available Qur'an suras with progress tracking."""
import asyncio
import sys
import time
from pathlib import Path

import httpx

# Configuration
API_BASE_URL = "http://localhost:8000"
TIMEOUT = 300  # 5 minutes per sura


async def check_data_file():
    """Check what suras are available in the data file."""
    data_file = Path("data/quran_original_text.txt")
    if not data_file.exists():
        print(f"Error: Data file not found at {data_file}")
        return {}
    
    suras = {}
    with open(data_file, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            
            parts = line.split('|')
            if len(parts) >= 2:
                try:
                    sura_num = int(parts[0])
                    if sura_num not in suras:
                        suras[sura_num] = 0
                    suras[sura_num] += 1
                except ValueError:
                    continue
    
    return suras


async def get_processing_status(sura: int):
    """Check if a sura is already processed."""
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                f"{API_BASE_URL}/pipeline/status",
                params={"sura": sura},
                timeout=10
            )
            if response.status_code == 200:
                data = response.json()
                return data.get("overall_status", "unknown")
            return "unknown"
        except Exception:
            return "unknown"


async def process_sura(sura: int, retry_even_if_complete: bool = False):
    """Process a single sura."""
    async with httpx.AsyncClient() as client:
        try:
            # Check current status
            status = await get_processing_status(sura)
            if status == "completed" and not retry_even_if_complete:
                return {"status": "already_complete", "sura": sura}
            
            # Start processing
            response = await client.post(
                f"{API_BASE_URL}/pipeline/process-sura",
                params={"sura": sura},
                timeout=TIMEOUT
            )
            
            if response.status_code in [200, 202]:  # 202 = Accepted/Queued
                data = response.json()
                return {"status": "success", "sura": sura, "data": data}
            else:
                return {
                    "status": "error",
                    "sura": sura,
                    "error": f"HTTP {response.status_code}",
                    "details": response.text[:200]
                }
        
        except httpx.TimeoutException:
            return {
                "status": "timeout",
                "sura": sura,
                "error": f"Timeout after {TIMEOUT}s"
            }
        except Exception as e:
            return {
                "status": "error",
                "sura": sura,
                "error": str(e)
            }


async def wait_for_completion(sura: int, max_wait: int = 60):
    """Wait for sura processing to complete."""
    start_time = time.time()
    last_status = None
    
    while time.time() - start_time < max_wait:
        status = await get_processing_status(sura)
        
        if status != last_status:
            print(f"      Status: {status}")
            last_status = status
        
        if status == "completed":
            return True
        elif status == "failed":
            return False
        
        await asyncio.sleep(2)
    
    print(f"      Warning: Timed out waiting for completion status")
    return None


async def get_stats():
    """Get current database statistics."""
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(f"{API_BASE_URL}/quran/stats", timeout=10)
            if response.status_code == 200:
                return response.json()
        except Exception:
            pass
    return None


async def main():
    """Main processing function."""
    print("=" * 70)
    print("  Qur'an Processing Pipeline - Batch Processor")
    print("=" * 70)
    print()
    
    # Check what data we have
    print("[1/4] Checking available data...")
    suras_available = await check_data_file()
    
    if not suras_available:
        print("Error: No valid sura data found in data/quran_original_text.txt")
        print()
        print("To process the full Qur'an, please download complete data from:")
        print("  - Tanzil Project: https://tanzil.net/download/")
        print("  - Format should be: sura|aya|arabic_text")
        return
    
    print(f"Found {len(suras_available)} suras in data file:")
    for sura, verse_count in sorted(suras_available.items()):
        print(f"  Sura {sura}: {verse_count} verses")
    print()
    
    # Check initial stats
    print("[2/4] Checking current database status...")
    initial_stats = await get_stats()
    if initial_stats:
        print(f"  Current: {initial_stats['total_tokens']} tokens, "
              f"{initial_stats['total_verses']} verses, "
              f"{initial_stats['total_roots']} roots")
    else:
        print("  Unable to fetch current stats")
    print()
    
    # Process each sura
    print("[3/4] Processing suras...")
    print("-" * 70)
    
    results = {
        "success": [],
        "already_complete": [],
        "error": [],
        "timeout": []
    }
    
    sura_list = sorted(suras_available.keys())
    total_suras = len(sura_list)
    
    for idx, sura in enumerate(sura_list, 1):
        print(f"\n[{idx}/{total_suras}] Processing Sura {sura} "
              f"({suras_available[sura]} verses)...")
        
        result = await process_sura(sura)
        status = result["status"]
        
        if status == "success":
            print(f"    ✓ Pipeline started successfully")
            # Wait a bit for processing
            await wait_for_completion(sura, max_wait=30)
            results["success"].append(sura)
        
        elif status == "already_complete":
            print(f"    ✓ Already processed (skipping)")
            results["already_complete"].append(sura)
        
        elif status == "timeout":
            print(f"    ✗ Timeout: {result['error']}")
            print(f"      (Processing may still continue in background)")
            results["timeout"].append(sura)
        
        else:  # error
            print(f"    ✗ Error: {result.get('error', 'Unknown error')}")
            if 'details' in result:
                print(f"      Details: {result['details']}")
            results["error"].append(sura)
        
        # Small delay between requests
        if idx < total_suras:
            await asyncio.sleep(1)
    
    # Final statistics
    print()
    print("-" * 70)
    print("[4/4] Final Results")
    print("=" * 70)
    print()
    
    print(f"Processed:        {len(results['success'])} suras")
    print(f"Already Complete: {len(results['already_complete'])} suras")
    print(f"Timeouts:         {len(results['timeout'])} suras")
    print(f"Errors:           {len(results['error'])} suras")
    print()
    
    if results['error']:
        print("Failed Suras:", ", ".join(map(str, results['error'])))
        print()
    
    # Get final stats
    print("Fetching final database statistics...")
    final_stats = await get_stats()
    if final_stats:
        print()
        print("Database Statistics:")
        print(f"  Total Tokens:  {final_stats['total_tokens']:,}")
        print(f"  Total Verses:  {final_stats['total_verses']:,}")
        print(f"  Total Roots:   {final_stats['total_roots']:,}")
        if 'suras' in final_stats:
            print(f"  Suras:         {final_stats['suras']}")
        
        if initial_stats:
            tokens_added = final_stats['total_tokens'] - initial_stats['total_tokens']
            verses_added = final_stats['total_verses'] - initial_stats['total_verses']
            roots_added = final_stats['total_roots'] - initial_stats['total_roots']
            
            print()
            print("Changes:")
            print(f"  Tokens Added:  +{tokens_added:,}")
            print(f"  Verses Added:  +{verses_added:,}")
            print(f"  Roots Added:   +{roots_added:,}")
    
    print()
    print("=" * 70)
    print("Processing complete!")
    print()
    print("To view the results, visit:")
    print(f"  {API_BASE_URL}/demo-enhanced")
    print()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\nProcessing interrupted by user.")
        print("Note: Background tasks may still be running in Celery worker.")
    except Exception as e:
        print(f"\n\nUnexpected error: {e}")
        import traceback
        traceback.print_exc()
