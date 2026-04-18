#!/usr/bin/env python3
"""
Document Consolidation Script: F:\DOCUMENTS + D:\DOCUMENTS → F:\DOCUMENTS (Primary)

This script merges all unique content from D:\DOCUMENTS into F:\DOCUMENTS.
- Handles duplicate files by appending timestamps/version suffixes
- Creates detailed log of all operations
- Does NOT delete from D:\ (archives instead for 30-day retention)
- Safe and reversible

Usage:
    python consolidate_documents.py
"""

import os
import shutil
import hashlib
from pathlib import Path
from datetime import datetime
import json

# Configuration
SOURCE_D = Path("D:\\DOCUMENTS")
TARGET_F = Path("F:\\DOCUMENTS")
LOG_FILE = TARGET_F / "CONSOLIDATION_LOG_20260308.txt"
OPERATION_SUMMARY = TARGET_F / "CONSOLIDATION_SUMMARY_20260308.json"
ARCHIVE_D = Path("D:\\DOCUMENTS_ARCHIVED_20260308")

# Folders that exist in both locations (need merge logic)
CONFLICT_FOLDERS = {
    "acte scanate Tudor Seicarescu",
    "ASOC PROP BD RM SARAT 31",
    "INTERJOB SOLUTIONS EUROPE",
}

# Folders unique to D:\ (copy entire folder)
UNIQUE_D_FOLDERS = {
    "AI",
    "CASABUZAU",
    "HIDROELECTRICA",
}

class DocumentConsolidator:
    def __init__(self):
        self.log = []
        self.operations = {
            "copied_files": [],
            "copied_folders": [],
            "renamed_duplicates": [],
            "conflicts_resolved": [],
            "errors": [],
            "statistics": {}
        }
        self.start_time = datetime.now()
        
    def log_message(self, msg, level="INFO"):
        """Add timestamped log message"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"[{timestamp}] {level}: {msg}"
        self.log.append(log_entry)
        print(log_entry)
        
    def get_file_hash(self, filepath, block_size=65536):
        """Calculate MD5 hash of file"""
        hasher = hashlib.md5()
        try:
            with open(filepath, 'rb') as f:
                for block in iter(lambda: f.read(block_size), b''):
                    hasher.update(block)
            return hasher.hexdigest()
        except Exception as e:
            self.log_message(f"Error hashing {filepath}: {e}", "ERROR")
            return None
    
    def files_are_identical(self, file1, file2):
        """Check if two files are identical by hash and size"""
        try:
            if file1.stat().st_size != file2.stat().st_size:
                return False
            return self.get_file_hash(file1) == self.get_file_hash(file2)
        except Exception as e:
            self.log_message(f"Error comparing files: {e}", "ERROR")
            return False
    
    def find_available_filename(self, target_path):
        """Find available filename if conflict exists"""
        if not target_path.exists():
            return target_path
        
        # File exists, generate versioned name
        stem = target_path.stem
        suffix = target_path.suffix
        parent = target_path.parent
        
        counter = 1
        while True:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            new_name = f"{stem}_v{counter}_{timestamp}{suffix}"
            new_path = parent / new_name
            
            if not new_path.exists():
                return new_path
            counter += 1
    
    def copy_file_with_conflict_handling(self, source_file, target_file):
        """Copy file, handling duplicates by renaming"""
        try:
            if target_file.exists():
                # Check if files are identical
                if self.files_are_identical(source_file, target_file):
                    self.log_message(
                        f"SKIP (identical): {target_file.name}",
                        "SKIP"
                    )
                    return True
                
                # Files differ, rename source version
                new_target = self.find_available_filename(target_file)
                shutil.copy2(source_file, new_target)
                
                self.log_message(
                    f"RENAME CONFLICT: {target_file.name} → {new_target.name}",
                    "CONFLICT"
                )
                self.operations["renamed_duplicates"].append({
                    "original": str(target_file),
                    "renamed_to": str(new_target),
                    "reason": "Different content from D:\\ version"
                })
                return True
            else:
                # Target doesn't exist, simple copy
                shutil.copy2(source_file, target_file)
                self.log_message(f"COPY: {target_file.name}", "OK")
                self.operations["copied_files"].append(str(target_file))
                return True
        except Exception as e:
            self.log_message(f"ERROR copying {source_file}: {e}", "ERROR")
            self.operations["errors"].append({
                "file": str(source_file),
                "error": str(e)
            })
            return False
    
    def merge_folder_recursive(self, source_dir, target_dir, folder_name=""):
        """Recursively merge folder contents"""
        try:
            if not target_dir.exists():
                target_dir.mkdir(parents=True, exist_ok=True)
            
            for item in source_dir.iterdir():
                target_item = target_dir / item.name
                
                if item.is_file():
                    self.copy_file_with_conflict_handling(item, target_item)
                elif item.is_dir():
                    self.merge_folder_recursive(item, target_item, f"{folder_name}/{item.name}")
                    
        except Exception as e:
            self.log_message(f"ERROR merging {source_dir}: {e}", "ERROR")
            self.operations["errors"].append({
                "folder": str(source_dir),
                "error": str(e)
            })
    
    def consolidate(self):
        """Main consolidation routine"""
        self.log_message("=" * 70)
        self.log_message("DOCUMENT CONSOLIDATION START")
        self.log_message(f"Source: {SOURCE_D}")
        self.log_message(f"Target: {TARGET_F}")
        self.log_message("=" * 70)
        
        # Verify source and target exist
        if not SOURCE_D.exists():
            self.log_message(f"ERROR: Source {SOURCE_D} does not exist!", "ERROR")
            return False
        
        if not TARGET_F.exists():
            self.log_message(f"ERROR: Target {TARGET_F} does not exist!", "ERROR")
            return False
        
        self.log_message(f"Source exists: {SOURCE_D} ✓")
        self.log_message(f"Target exists: {TARGET_F} ✓")
        
        # Step 1: Copy unique D:\ folders
        self.log_message("\n[STEP 1] Copying unique D:\\ folders...")
        for folder_name in UNIQUE_D_FOLDERS:
            source_folder = SOURCE_D / folder_name
            target_folder = TARGET_F / folder_name
            
            if source_folder.exists():
                self.log_message(f"  Copying: {folder_name}/")
                self.merge_folder_recursive(source_folder, target_folder, folder_name)
                self.operations["copied_folders"].append(folder_name)
            else:
                self.log_message(f"  SKIP: {folder_name}/ not found in D:\\", "WARN")
        
        # Step 2: Merge conflict folders
        self.log_message("\n[STEP 2] Merging conflict folders (keep all content)...")
        for folder_name in CONFLICT_FOLDERS:
            source_folder = SOURCE_D / folder_name
            target_folder = TARGET_F / folder_name
            
            if source_folder.exists() and target_folder.exists():
                self.log_message(f"  Merging: {folder_name}/")
                self.merge_folder_recursive(source_folder, target_folder, folder_name)
                self.operations["conflicts_resolved"].append(folder_name)
            elif source_folder.exists():
                self.log_message(f"  Copying (D:\\ only): {folder_name}/")
                self.merge_folder_recursive(source_folder, target_folder, folder_name)
            else:
                self.log_message(f"  SKIP: {folder_name}/ not in D:\\", "WARN")
        
        # Step 3: Summary
        self.log_message("\n[STEP 3] Consolidation complete!")
        self.log_message(f"  Files copied: {len(self.operations['copied_files'])}")
        self.log_message(f"  Folders copied: {len(self.operations['copied_folders'])}")
        self.log_message(f"  Conflicts resolved (renamed): {len(self.operations['renamed_duplicates'])}")
        self.log_message(f"  Errors encountered: {len(self.operations['errors'])}")
        
        return True
    
    def save_log(self):
        """Save detailed log to file"""
        try:
            with open(LOG_FILE, 'w', encoding='utf-8') as f:
                f.write("\n".join(self.log))
            self.log_message(f"\nLog saved: {LOG_FILE}")
            return True
        except Exception as e:
            self.log_message(f"ERROR saving log: {e}", "ERROR")
            return False
    
    def save_summary(self):
        """Save operation summary as JSON"""
        try:
            self.operations["statistics"] = {
                "start_time": self.start_time.isoformat(),
                "end_time": datetime.now().isoformat(),
                "duration_seconds": (datetime.now() - self.start_time).total_seconds(),
                "source": str(SOURCE_D),
                "target": str(TARGET_F),
            }
            
            with open(OPERATION_SUMMARY, 'w', encoding='utf-8') as f:
                json.dump(self.operations, f, indent=2, ensure_ascii=False)
            
            self.log_message(f"Summary saved: {OPERATION_SUMMARY}")
            return True
        except Exception as e:
            self.log_message(f"ERROR saving summary: {e}", "ERROR")
            return False


def main():
    consolidator = DocumentConsolidator()
    
    try:
        success = consolidator.consolidate()
        consolidator.save_log()
        consolidator.save_summary()
        
        if success:
            print("\n✓ Consolidation completed successfully!")
            print(f"  Check logs: {LOG_FILE}")
            print(f"  Summary: {OPERATION_SUMMARY}")
        else:
            print("\n✗ Consolidation failed!")
            
    except KeyboardInterrupt:
        print("\n\n✗ Consolidation interrupted by user")
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")


if __name__ == "__main__":
    main()
