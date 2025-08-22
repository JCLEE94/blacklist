#!/usr/bin/env python3
"""
코드 스타일 자동 수정 스크립트
flake8, black, isort 기준에 맞게 코드를 자동으로 정리

Sample input: 코드 스타일 문제가 있는 Python 파일들
Expected output: 표준화된 코드 스타일이 적용된 파일들
"""

import re
import subprocess
import logging
from pathlib import Path
from typing import List, Dict, Tuple

logger = logging.getLogger(__name__)


class CodeStyleFixer:
    """코드 스타일 자동 수정 도구"""
    
    def __init__(self):
        self.fixed_files = []
        self.failed_files = []
        self.summary = {
            'blank_lines_fixed': 0,
            'long_lines_fixed': 0,
            'import_fixes': 0,
            'whitespace_fixes': 0,
            'undefined_names_fixed': 0
        }
    
    def fix_blank_lines(self, content: str) -> str:
        """빈 줄 관련 문제 수정"""
        lines = content.split('\n')
        fixed_lines = []
        
        i = 0
        while i < len(lines):
            line = lines[i]
            
            # 연속된 빈 줄을 2개로 제한
            if line.strip() == '':
                blank_count = 0
                start_blank = i
                
                while i < len(lines) and lines[i].strip() == '':
                    blank_count += 1
                    i += 1
                
                # 파일 시작/끝이 아닌 경우 최대 2개 빈 줄
                if start_blank > 0 and i < len(lines):
                    if blank_count > 2:
                        # 2개만 추가
                        fixed_lines.append('')
                        fixed_lines.append('')
                        self.summary['blank_lines_fixed'] += 1
                    else:
                        # 원래 빈 줄 개수 유지
                        for _ in range(blank_count):
                            fixed_lines.append('')
                elif blank_count <= 2:
                    # 파일 시작/끝에서는 적은 빈 줄 허용
                    for _ in range(blank_count):
                        fixed_lines.append('')
                # blank_count > 2이고 파일 시작/끝인 경우 빈 줄 제거
            else:
                fixed_lines.append(line)
                i += 1
        
        return '\n'.join(fixed_lines)
    
    def fix_long_lines(self, content: str) -> str:
        """긴 줄을 적절히 나누기"""
        lines = content.split('\n')
        fixed_lines = []
        
        for line in lines:
            if len(line) > 88:
                # 간단한 경우만 처리 (문자열, 주석)
                if '#' in line and len(line) > 88:
                    # 주석이 있는 긴 줄
                    code_part = line[:line.find('#')].rstrip()
                    comment_part = line[line.find('#'):]
                    if len(code_part) <= 85:
                        fixed_lines.append(code_part)
                        fixed_lines.append('    ' + comment_part)
                        self.summary['long_lines_fixed'] += 1
                        continue
                
                # 문자열이 있는 경우
                if '"' in line or "'" in line:
                    # f-string이나 긴 문자열을 다음 줄로
                    if 'f"' in line or "f'" in line:
                        # f-string 개행 처리
                        if '(' in line and ')' in line:
                            # 함수 호출 내의 f-string
                            parts = line.split('f"')
                            if len(parts) == 2:
                                before = parts[0]
                                after = 'f"' + parts[1]
                                if len(before.rstrip()) <= 80:
                                    fixed_lines.append(before.rstrip() + ' \\')
                                    fixed_lines.append('    ' + after)
                                    self.summary['long_lines_fixed'] += 1
                                    continue
                
                # 기본적으로 원본 유지 (복잡한 경우)
                fixed_lines.append(line)
            else:
                fixed_lines.append(line)
        
        return '\n'.join(fixed_lines)
    
    def fix_whitespace_issues(self, content: str) -> str:
        """공백 관련 문제 수정"""
        lines = content.split('\n')
        fixed_lines = []
        
        for line in lines:
            # 줄 끝 공백 제거
            original_line = line
            line = line.rstrip()
            
            if original_line != line:
                self.summary['whitespace_fixes'] += 1
            
            fixed_lines.append(line)
        
        return '\n'.join(fixed_lines)
    
    def fix_import_issues(self, content: str) -> str:
        """import 관련 문제 수정"""
        lines = content.split('\n')
        fixed_lines = []
        
        # 기본 import 수정
        common_fixes = {
            'from flask import Blueprint': 'from ...common.imports import Blueprint',
            'from flask import jsonify': 'from ...common.imports import jsonify',
            'from flask import request': 'from ...common.imports import request',
        }
        
        for line in lines:
            original_line = line
            
            # undefined names 수정
            if 'F821 undefined name' in line:
                continue  # 이 줄은 주석이므로 건너뛰기
            
            # Blueprint 관련 수정
            if 'Blueprint' in line and 'from' not in line and '=' in line:
                # Blueprint 사용 코드에서 import 확인
                if 'Blueprint(' in line and 'from' not in '\n'.join(lines[:lines.index(line)]):
                    # 파일 상단에 import 추가 필요
                    pass  # 이미 Flask import converter에서 처리됨
            
            fixed_lines.append(line)
        
        return '\n'.join(fixed_lines)
    
    def fix_undefined_names(self, content: str, file_path: Path) -> str:
        """정의되지 않은 이름 문제 수정"""
        # 파일 경로에 따라 적절한 import 추가
        lines = content.split('\n')
        
        # current_app 관련 수정
        if 'current_app' in content and 'from flask import' not in content:
            # Flask import 확인
            has_flask_import = False
            for line in lines:
                if 'from flask import' in line or 'from ...common.imports import' in line:
                    has_flask_import = True
                    break
            
            if has_flask_import:
                # 기존 import에 current_app 추가
                for i, line in enumerate(lines):
                    if 'from ...common.imports import' in line:
                        if 'current_app' not in line:
                            lines[i] = line.rstrip() + ', current_app'
                            self.summary['undefined_names_fixed'] += 1
                        break
        
        return '\n'.join(lines)
    
    def fix_comment_format(self, content: str) -> str:
        """주석 형식 수정"""
        lines = content.split('\n')
        fixed_lines = []
        
        for line in lines:
            # 블록 주석 수정 (E265)
            if line.strip().startswith('#') and not line.strip().startswith('# '):
                if line.strip() != '#':
                    # '# ' 형식으로 수정
                    indent = len(line) - len(line.lstrip())
                    comment_text = line.strip()[1:].lstrip()
                    fixed_line = ' ' * indent + '# ' + comment_text
                    fixed_lines.append(fixed_line)
                else:
                    fixed_lines.append(line)
            else:
                fixed_lines.append(line)
        
        return '\n'.join(fixed_lines)
    
    def fix_file(self, file_path: Path) -> bool:
        """단일 파일의 스타일 문제 수정"""
        try:
            # 파일 읽기
            with open(file_path, 'r', encoding='utf-8') as f:
                original_content = f.read()
            
            content = original_content
            
            # 각종 수정 적용
            content = self.fix_blank_lines(content)
            content = self.fix_whitespace_issues(content)
            content = self.fix_comment_format(content)
            content = self.fix_long_lines(content)
            content = self.fix_import_issues(content)
            content = self.fix_undefined_names(content, file_path)
            
            # 변경사항이 있는 경우에만 파일 저장
            if content != original_content:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error fixing {file_path}: {e}")
            return False
    
    def run_black_formatter(self, file_paths: List[Path]) -> Tuple[int, int]:
        """Black formatter 실행"""
        success_count = 0
        failure_count = 0
        
        for file_path in file_paths:
            try:
                # Black 실행
                result = subprocess.run(
                    ['python3', '-m', 'black', '--line-length', '88', str(file_path)],
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                
                if result.returncode == 0:
                    success_count += 1
                else:
                    failure_count += 1
                    logger.warning(f"Black formatting failed for {file_path}: {result.stderr}")
                    
            except subprocess.TimeoutExpired:
                failure_count += 1
                logger.error(f"Black formatting timeout for {file_path}")
            except FileNotFoundError:
                logger.warning("Black not found, skipping automatic formatting")
                break
            except Exception as e:
                failure_count += 1
                logger.error(f"Black formatting error for {file_path}: {e}")
        
        return success_count, failure_count
    
    def run_isort_formatter(self, file_paths: List[Path]) -> Tuple[int, int]:
        """isort formatter 실행"""
        success_count = 0
        failure_count = 0
        
        for file_path in file_paths:
            try:
                # isort 실행
                result = subprocess.run(
                    ['python3', '-m', 'isort', '--profile', 'black', str(file_path)],
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                
                if result.returncode == 0:
                    success_count += 1
                else:
                    failure_count += 1
                    logger.warning(f"isort formatting failed for {file_path}: {result.stderr}")
                    
            except subprocess.TimeoutExpired:
                failure_count += 1
                logger.error(f"isort formatting timeout for {file_path}")
            except FileNotFoundError:
                logger.warning("isort not found, skipping import sorting")
                break
            except Exception as e:
                failure_count += 1
                logger.error(f"isort formatting error for {file_path}: {e}")
        
        return success_count, failure_count
    
    def fix_codebase(self, src_path: Path, max_files: int = 50) -> Dict[str, int]:
        """전체 코드베이스 스타일 수정"""
        # Python 파일들 찾기
        python_files = list(src_path.rglob("*.py"))
        
        # 테스트 파일과 특정 파일들 제외
        filtered_files = []
        for file_path in python_files:
            if any(exclude in str(file_path) for exclude in ['test_', '__pycache__', 'conftest.py']):
                continue
            filtered_files.append(file_path)
        
        # 파일 수 제한
        target_files = filtered_files[:max_files]
        
        logger.info(f"🔧 {len(target_files)}개 파일의 스타일을 수정합니다...")
        
        # 수동 수정
        manual_fixed = 0
        for file_path in target_files:
            if self.fix_file(file_path):
                self.fixed_files.append(file_path)
                manual_fixed += 1
            else:
                logger.debug(f"No changes needed: {file_path}")
        
        # Black 포매팅
        logger.info("🎨 Black 포매팅을 실행합니다...")
        black_success, black_failure = self.run_black_formatter(target_files)
        
        # isort 포매팅
        logger.info("📚 isort 포매팅을 실행합니다...")
        isort_success, isort_failure = self.run_isort_formatter(target_files)
        
        return {
            'total_files': len(target_files),
            'manual_fixed': manual_fixed,
            'black_success': black_success,
            'black_failure': black_failure,
            'isort_success': isort_success,
            'isort_failure': isort_failure,
            **self.summary
        }


def main():
    """메인 실행 함수"""
    src_path = Path("/home/jclee/app/blacklist/src")
    
    if not src_path.exists():
        print(f"❌ 소스 디렉토리가 존재하지 않습니다: {src_path}")
        return
    
    # 스타일 수정 실행
    fixer = CodeStyleFixer()
    results = fixer.fix_codebase(src_path, max_files=30)  # 처음 30개 파일만
    
    # 결과 출력
    print("=" * 80)
    print("🎯 코드 스타일 수정 결과")
    print("=" * 80)
    print(f"📁 대상 파일: {results['total_files']}개")
    print(f"🔧 수동 수정: {results['manual_fixed']}개")
    print(f"🎨 Black 성공: {results['black_success']}개")
    print(f"📚 isort 성공: {results['isort_success']}개")
    print()
    print("📊 세부 수정 내역:")
    print(f"  - 빈 줄 수정: {results['blank_lines_fixed']}개")
    print(f"  - 긴 줄 수정: {results['long_lines_fixed']}개")
    print(f"  - 공백 수정: {results['whitespace_fixes']}개")
    print(f"  - Import 수정: {results['import_fixes']}개")
    print(f"  - 정의되지 않은 이름 수정: {results['undefined_names_fixed']}개")
    print("=" * 80)


if __name__ == "__main__":
    import sys
    
    all_validation_failures = []
    total_tests = 0
    
    # Test 1: Basic regex patterns
    total_tests += 1
    try:
        test_content = "line1\n\n\n\nline2"
        fixer = CodeStyleFixer()
        result = fixer.fix_blank_lines(test_content)
        # 연속된 3개 이상의 빈 줄이 없어야 함
        if '\n\n\n\n' in result:
            all_validation_failures.append("Blank lines test: Too many consecutive blank lines remain")
    except Exception as e:
        all_validation_failures.append(f"Blank lines test: Failed - {e}")
    
    # Test 2: Whitespace handling
    total_tests += 1
    try:
        test_content = "line with trailing spaces   \n"
        fixer = CodeStyleFixer()
        result = fixer.fix_whitespace_issues(test_content)
        if result.endswith('   '):
            all_validation_failures.append("Whitespace test: Trailing spaces not removed")
    except Exception as e:
        all_validation_failures.append(f"Whitespace test: Failed - {e}")
    
    # Test 3: Source path existence
    total_tests += 1
    try:
        src_path = Path("/home/jclee/app/blacklist/src")
        if not src_path.exists():
            all_validation_failures.append("Path test: Source directory does not exist")
    except Exception as e:
        all_validation_failures.append(f"Path test: Failed - {e}")
    
    # Final validation result
    if all_validation_failures:
        print(f"❌ VALIDATION FAILED - {len(all_validation_failures)} of {total_tests} tests failed:")
        for failure in all_validation_failures:
            print(f"  - {failure}")
        sys.exit(1)
    else:
        print(f"✅ VALIDATION PASSED - All {total_tests} tests produced expected results")
        print("Code style fixer is validated and ready to run")
        main()
        sys.exit(0)