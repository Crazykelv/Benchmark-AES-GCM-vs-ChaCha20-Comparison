#!/usr/bin/env python3
"""
Kelompok : 
Anggota :
Riskyta 227006050
Fahri Aminuddin Abdillah 227006051
Faiq Pataya Zain 227006052

Perbandingan Performa AES-GCM vs ChaCha20-Poly1305 pada file.


Penggunaan:
    python benchmark.py --files tes_10MB.bin tes_100MB.bin tes_500MB.bin tes_1GB.bin
    python benchmark.py --files /path/to/*.bin --iters 10 --outdir results

Outputs (in outdir):
 - raw_results.csv      : tiap run (file, cipher, iter, wall_time, cpu_time, bytes_processed)
 - summary_avg.csv      : rata-rata per file size & cipher
 - time_avg.png         : bar chart average wall time
 - cpu_avg.png          : bar chart average CPU time
"""

import argparse
import os
import sys
import time
import csv
import tempfile
import secrets
from pathlib import Path
from typing import List, Dict

try:
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM, ChaCha20Poly1305
except Exception as e:
    print("Error: module 'cryptography' diperlukan. Install: pip install cryptography")
    raise

try:
    import pandas as pd
    import matplotlib.pyplot as plt
except Exception as e:
    print("Error: module 'pandas' and 'matplotlib' diperlukan. Install: pip install pandas matplotlib")
    raise

# ---------- helpers ----------
def human_bytes(n: int) -> str:
    for unit in ['B','KB','MB','GB','TB']:
        if n < 1024:
            return f"{n:.2f}{unit}"
        n /= 1024
    return f"{n:.2f}PB"

def encrypt_aes_gcm(key: bytes, plaintext: bytes) -> bytes:
    # AESGCM expects 12-byte nonce commonly
    aesgcm = AESGCM(key)
    nonce = secrets.token_bytes(12)
    return nonce + aesgcm.encrypt(nonce, plaintext, associated_data=None)

def encrypt_chacha(key: bytes, plaintext: bytes) -> bytes:
    chacha = ChaCha20Poly1305(key)
    nonce = secrets.token_bytes(12)
    return nonce + chacha.encrypt(nonce, plaintext, associated_data=None)

# ---------- benchmark single file & cipher ----------
def run_single_encryption(file_path: Path, cipher_name: str, key: bytes, outdir: Path) -> Dict:
    """
    Read file, encrypt, write ciphertext to temporary file in outdir.
    Return dict with metrics.
    """
    size = file_path.stat().st_size
    # read file entirely (note: for very large files this will use RAM)
    start_wall_read = time.perf_counter()
    with open(file_path, "rb") as f:
        plaintext = f.read()
    end_wall_read = time.perf_counter()

    # measure encryption (including cpu time)
    start_wall = time.perf_counter()
    start_cpu = time.process_time()
    if cipher_name == "AES-GCM":
        ciphertext = encrypt_aes_gcm(key, plaintext)
    elif cipher_name == "ChaCha20-Poly1305":
        ciphertext = encrypt_chacha(key, plaintext)
    else:
        raise ValueError("Unsupported cipher")
    end_cpu = time.process_time()
    end_wall = time.perf_counter()

    # write ciphertext to temp file to include I/O (so we simulate real workload)
    out_file = outdir / f"{file_path.name}.{cipher_name.replace(' ','')}.ct"
    with open(out_file, "wb") as outf:
        outf.write(ciphertext)

    return {
        "file": str(file_path),
        "filesize_bytes": size,
        "cipher": cipher_name,
        "wall_time_sec": end_wall - start_wall + (end_wall_read - start_wall_read),  # include read time
        "cpu_time_sec": end_cpu - start_cpu,
        "output_file": str(out_file),
        "timestamp": time.time(),
        "bytes_processed": len(plaintext),
    }

# ---------- main runner ----------
def benchmark(files: List[Path], iters: int, outdir: Path, keep_outputs: bool):
    outdir.mkdir(parents=True, exist_ok=True)
    raw_rows = []

    ciphers = ["AES-GCM", "ChaCha20-Poly1305"]
    # Use same key per cipher for fairness
    key_aes = secrets.token_bytes(32)  # AES-256-GCM
    key_cha = secrets.token_bytes(32)  # ChaCha20-Poly1305 uses 32-byte key

    total_runs = len(files) * len(ciphers) * iters
    run_idx = 0

    print(f"Starting benchmark: {len(files)} files x {len(ciphers)} ciphers x {iters} iters = {total_runs} runs")
    print(f"Output directory: {outdir.resolve()}")
    start_all = time.perf_counter()
    for file_path in files:
        filesize = file_path.stat().st_size
        print(f"\nFile: {file_path} ({human_bytes(filesize)})")
        for cipher in ciphers:
            print(f"  Cipher: {cipher}")
            # reuse same key each iteration per cipher, so generate once
            for i in range(1, iters + 1):
                run_idx += 1
                print(f"    Iter {i}/{iters} ... ", end="", flush=True)
                try:
                    key = key_aes if cipher == "AES-GCM" else key_cha
                    metrics = run_single_encryption(file_path, cipher, key, outdir)
                    metrics["iter"] = i
                    raw_rows.append(metrics)
                    print(f"done — wall {metrics['wall_time_sec']:.3f}s cpu {metrics['cpu_time_sec']:.3f}s")
                except Exception as e:
                    print(f"ERROR: {e}")
    elapsed_all = time.perf_counter() - start_all
    print(f"\nAll runs finished in {elapsed_all:.2f} seconds.")

    # Save raw csv
    raw_csv = outdir / "raw_results.csv"
    df = pd.DataFrame(raw_rows)
    df.to_csv(raw_csv, index=False)
    print(f"Saved raw results to {raw_csv}")

    # Compute averages grouped by filesize (or filename) and cipher
    # We'll group by filesize rounded to human-friendly labels
    df["filesize_MB"] = df["filesize_bytes"] / (1024*1024)
    # Create label for X-axis choosing conventional sizes if match else filename
    def size_label(row):
        size_mb = row["filesize_MB"]
        if abs(size_mb - 10) < 1:
            return "10MB"
        if abs(size_mb - 100) < 5:
            return "100MB"
        if abs(size_mb - 500) < 20:
            return "500MB"
        if abs(size_mb - 1024) < 100:
            return "1GB"
        # fallback to file name
        return Path(row["file"]).name

    df["size_label"] = df.apply(size_label, axis=1)

    summary = df.groupby(["size_label", "cipher"]).agg(
        runs=("iter","count"),
        avg_wall_sec=("wall_time_sec","mean"),
        std_wall_sec=("wall_time_sec","std"),
        avg_cpu_sec=("cpu_time_sec","mean"),
        std_cpu_sec=("cpu_time_sec","std"),
        bytes_processed=("bytes_processed","mean"),
    ).reset_index()

    summary_csv = outdir / "summary_avg.csv"
    summary.to_csv(summary_csv, index=False)
    print(f"Saved summary averages to {summary_csv}")

    # Plotting: average wall time bar chart
    plt.figure(figsize=(10,6))
    # pivot table for plotting
    pivot_wall = summary.pivot(index="size_label", columns="cipher", values="avg_wall_sec")
    pivot_wall = pivot_wall.sort_index()
    pivot_wall.plot(kind="bar", rot=0)
    plt.title("Average Wall Time (sec) — AES-GCM vs ChaCha20-Poly1305")
    plt.ylabel("Average wall time (s)")
    plt.xlabel("File size")
    plt.tight_layout()
    time_png = outdir / "time_avg.png"
    plt.savefig(time_png)
    plt.close()
    print(f"Saved chart {time_png}")

    # Plotting: average CPU time bar chart
    plt.figure(figsize=(10,6))
    pivot_cpu = summary.pivot(index="size_label", columns="cipher", values="avg_cpu_sec")
    pivot_cpu = pivot_cpu.sort_index()
    pivot_cpu.plot(kind="bar", rot=0)
    plt.title("Average CPU Time (sec) — AES-GCM vs ChaCha20-Poly1305")
    plt.ylabel("Average CPU time (s)")
    plt.xlabel("File size")
    plt.tight_layout()
    cpu_png = outdir / "cpu_avg.png"
    plt.savefig(cpu_png)
    plt.close()
    print(f"Saved chart {cpu_png}")

    # Optionally cleanup ciphertext outputs to save space
    if not keep_outputs:
        print("Cleaning up temporary ciphertext files ...")
        for f in df["output_file"].unique():
            try:
                os.remove(f)
            except Exception:
                pass

    print("Benchmark complete.")

# ---------- CLI ----------
def parse_args():
    ap = argparse.ArgumentParser(description="Benchmark AES-GCM vs ChaCha20-Poly1305 on files")
    ap.add_argument("--files", nargs="+", required=True,
                    help="List of file paths to test (supports glob if expanded by shell)")
    ap.add_argument("--iters", type=int, default=10, help="Iterations per file/cipher (default: 10)")
    ap.add_argument("--outdir", type=str, default="benchmark_results", help="Output directory")
    ap.add_argument("--keep-outputs", action="store_true", help="Keep ciphertext output files (default: remove)")
    return ap.parse_args()

def main():
    args = parse_args()
    files = [Path(f) for f in args.files]
    # Validate files exist
    missing = [str(f) for f in files if not f.exists()]
    if missing:
        print("ERROR: these files do not exist:")
        for m in missing:
            print("  ", m)
        sys.exit(1)

    benchmark(files, args.iters, Path(args.outdir), args.keep_outputs)

if __name__ == "__main__":
    main()
