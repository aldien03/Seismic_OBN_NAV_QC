"""
Performance Profiling Script

Profiles the QC validation process to identify bottlenecks.
Uses cProfile and line_profiler to measure execution time.

Usage:
    python profile_performance.py

Output:
    - Performance report to console
    - Detailed profile stats saved to profile_results.txt
"""

import cProfile
import pstats
import io
import time
import sys
import os
import pandas as pd
import logging
from configparser import ConfigParser

# Add current directory to path
sys.path.insert(0, os.path.dirname(__file__))

# Import modules to profile
from config_manager import ConfigManager
from data_importers import SPSImporter, SPSCompImporter, EOLImporter, ASCImporter, SBSImporter
from qc_validator import QCValidator
from qc_report_generator import QCReportGenerator

# Suppress logging during profiling
logging.basicConfig(level=logging.WARNING)


def create_sample_dataframe(num_rows=1000):
    """
    Create sample DataFrame for performance testing.

    Args:
        num_rows: Number of rows to generate

    Returns:
        DataFrame with sample QC data
    """
    import numpy as np

    # Generate realistic sample data
    data = {
        'shot_point': range(1001, 1001 + num_rows),
        'sequence': [256] * num_rows,
        'line_name': ['3184P31885'] * num_rows,
        'easting_m': np.random.uniform(123000, 124000, num_rows),
        'northing_m': np.random.uniform(7650000, 7660000, num_rows),
        'sti': np.random.uniform(5.8, 6.3, num_rows),
        'sub_array_sep': np.random.uniform(6.5, 9.5, num_rows),
        'cos_dual': np.random.uniform(32, 43, num_rows),
        'volume': np.random.uniform(2900, 3100, num_rows),
        'gun_depth': np.random.uniform(-8.5, -5.5, num_rows),
        'gun_pressure': np.random.uniform(1850, 2150, num_rows),
        'gun_timing': np.random.uniform(0.0, 2.5, num_rows),
        'crossline': np.random.uniform(0, 12, num_rows),
        'radial': np.random.uniform(0, 12, num_rows),
        'sma': np.random.uniform(0, 4, num_rows),
    }

    return pd.DataFrame(data)


def profile_qc_validation(num_rows=1000):
    """
    Profile the QC validation process.

    Args:
        num_rows: Number of rows to test with
    """
    print(f"\n{'='*80}")
    print(f"Performance Profiling: QC Validation ({num_rows:,} rows)")
    print(f"{'='*80}\n")

    # Load configuration
    config = ConfigManager()

    # Create QC validator
    validator = QCValidator(config)

    # Create sample data
    print(f"Creating sample DataFrame with {num_rows:,} rows...")
    df = create_sample_dataframe(num_rows)
    print(f"DataFrame created: {df.shape[0]} rows x {df.shape[1]} columns")
    print(f"Memory usage: {df.memory_usage(deep=True).sum() / 1024**2:.2f} MB\n")

    # Profile validation
    print("Profiling QC validation...")

    profiler = cProfile.Profile()
    profiler.enable()

    start_time = time.time()
    result_df = validator.validate_data(df)
    end_time = time.time()

    profiler.disable()

    elapsed = end_time - start_time
    rows_per_sec = num_rows / elapsed if elapsed > 0 else 0

    print(f"\n{'='*80}")
    print(f"Performance Results:")
    print(f"{'='*80}")
    print(f"Total time: {elapsed:.3f} seconds")
    print(f"Rows processed: {num_rows:,}")
    print(f"Throughput: {rows_per_sec:,.0f} rows/second")
    print(f"Time per row: {(elapsed/num_rows)*1000:.2f} ms\n")

    # Print top time-consuming functions
    print(f"{'='*80}")
    print(f"Top 20 Time-Consuming Functions:")
    print(f"{'='*80}\n")

    s = io.StringIO()
    stats = pstats.Stats(profiler, stream=s)
    stats.strip_dirs()
    stats.sort_stats('cumulative')
    stats.print_stats(20)

    profile_output = s.getvalue()
    print(profile_output)

    # Save detailed results
    with open('profile_results.txt', 'w') as f:
        f.write(f"Performance Profiling Results\n")
        f.write(f"{'='*80}\n\n")
        f.write(f"Dataset: {num_rows:,} rows\n")
        f.write(f"Total time: {elapsed:.3f} seconds\n")
        f.write(f"Throughput: {rows_per_sec:,.0f} rows/second\n\n")
        f.write(f"{'='*80}\n")
        f.write(f"Detailed Function Statistics:\n")
        f.write(f"{'='*80}\n\n")
        f.write(profile_output)

        # Write full stats
        s = io.StringIO()
        stats = pstats.Stats(profiler, stream=s)
        stats.strip_dirs()
        stats.sort_stats('cumulative')
        stats.print_stats()
        f.write(s.getvalue())

    print(f"\nDetailed results saved to: profile_results.txt")

    return elapsed, rows_per_sec


def profile_data_merging():
    """Profile DataFrame merging operations."""
    print(f"\n{'='*80}")
    print(f"Performance Profiling: DataFrame Merging")
    print(f"{'='*80}\n")

    # Create sample dataframes
    num_rows = 1000

    sps_df = pd.DataFrame({
        'shot_point': range(1001, 1001 + num_rows),
        'easting_m': [123000.0] * num_rows,
        'northing_m': [7650000.0] * num_rows,
    })

    comp_df = pd.DataFrame({
        'shot_point': range(1001, 1001 + num_rows),
        'radial': [5.0] * num_rows,
    })

    eol_df = pd.DataFrame({
        'shot_point': range(1001, 1001 + num_rows),
        'sti': [6.0] * num_rows,
    })

    print(f"Testing merge of 3 DataFrames ({num_rows:,} rows each)...")

    start_time = time.time()

    # Perform merges
    merged = sps_df.copy()
    merged['shot_point'] = merged['shot_point'].astype(str).str.zfill(4)

    for name, df in [('comp', comp_df), ('eol', eol_df)]:
        df['shot_point'] = df['shot_point'].astype(str).str.zfill(4)
        merged = pd.merge(merged, df, on='shot_point', how='left', suffixes=('', f'_{name}'))

    end_time = time.time()

    elapsed = end_time - start_time
    print(f"Merge time: {elapsed:.3f} seconds")
    print(f"Result shape: {merged.shape}")

    return elapsed


def profile_percentage_calculation():
    """Profile error percentage calculations."""
    print(f"\n{'='*80}")
    print(f"Performance Profiling: Percentage Calculations")
    print(f"{'='*80}\n")

    num_rows = 10000
    df = create_sample_dataframe(num_rows)

    # Add flag columns
    df['sti_flag'] = (df['sti'] > 6.0).astype(int) * 2
    df['volume_flag'] = (df['volume'] < 2950).astype(int) * 2
    df['gun_depth_flag'] = (df['gun_depth'] < -8.0).astype(int) * 2

    config = ConfigManager()
    generator = QCReportGenerator(config)

    print(f"Calculating percentages for {num_rows:,} rows...")

    start_time = time.time()
    percentages = generator.calculate_percentages(df, num_rows)
    end_time = time.time()

    elapsed = end_time - start_time
    print(f"Calculation time: {elapsed:.3f} seconds")
    print(f"Results: {percentages}")

    return elapsed


def run_all_profiles():
    """Run all performance profiles."""
    print(f"\n{'#'*80}")
    print(f"# PXGEONavQC Performance Profiling Suite")
    print(f"{'#'*80}\n")

    results = {}

    # Test with different dataset sizes
    for num_rows in [100, 1000, 5000]:
        elapsed, throughput = profile_qc_validation(num_rows)
        results[f'qc_validation_{num_rows}'] = {
            'time': elapsed,
            'throughput': throughput
        }

    # Profile other operations
    results['data_merging'] = {'time': profile_data_merging()}
    results['percentage_calc'] = {'time': profile_percentage_calculation()}

    # Summary
    print(f"\n{'='*80}")
    print(f"Performance Summary:")
    print(f"{'='*80}\n")

    for test_name, metrics in results.items():
        if 'throughput' in metrics:
            print(f"{test_name:30s}: {metrics['time']:.3f}s ({metrics['throughput']:,.0f} rows/s)")
        else:
            print(f"{test_name:30s}: {metrics['time']:.3f}s")

    print(f"\n{'='*80}\n")

    return results


if __name__ == '__main__':
    try:
        results = run_all_profiles()
        print("Profiling complete!")
        sys.exit(0)
    except Exception as e:
        print(f"ERROR: Profiling failed: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
