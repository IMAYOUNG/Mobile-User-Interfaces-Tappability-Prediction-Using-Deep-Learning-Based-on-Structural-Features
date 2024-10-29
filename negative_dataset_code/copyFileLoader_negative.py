import os
import random
import shutil
import csv

# CSV 파일에서 에러난 앱 목록을 로드
def load_error_apps(csv_file):
    error_apps = set()
    try:
        with open(csv_file, newline='', encoding='utf-8') as csvfile:
            reader = csv.reader(csvfile)
            next(reader)  # 헤더를 건너뜀
            for row in reader:
                error_apps.add(row[0])
    except Exception as e:
        print(f"Error reading CSV file: {e}")
    return error_apps

# 유효한 앱을 필터링하여 리스트로 저장
def filter_valid_apps(filtered_traces_dir, error_apps):
    valid_apps = []
    for app_name in os.listdir(filtered_traces_dir):
        app_dir = os.path.join(filtered_traces_dir, app_name)
        if os.path.isdir(app_dir) and app_name not in error_apps:
            valid_apps.append(app_dir)
    return valid_apps

# 무작위로 100개의 UI 뷰 하이어라키와 스크린샷을 선택하여 복사
def copy_random_ui_files(valid_apps, output_dir, num_samples=100):
    os.makedirs(output_dir, exist_ok=True)
    selected_ui_files = 0
    selected_apps = set()

    while selected_ui_files < num_samples and len(selected_apps) < len(valid_apps):
        random_app_dir = random.choice(valid_apps)
        app_name = os.path.basename(random_app_dir)

        # 이미 선택한 앱은 다시 선택하지 않음
        if app_name in selected_apps:
            continue

        trace_dirs = [d for d in os.listdir(random_app_dir) if os.path.isdir(os.path.join(random_app_dir, d))]
        if not trace_dirs:
            continue

        random_trace_dir = os.path.join(random_app_dir, random.choice(trace_dirs))
        view_hierarchies_path = os.path.join(random_trace_dir, 'view_hierarchies')
        screenshots_path = os.path.join(random_trace_dir, 'screenshots')

        if os.path.exists(view_hierarchies_path) and os.listdir(view_hierarchies_path) and os.path.exists(screenshots_path):
            # 무작위로 하나의 뷰 하이어라키 파일과 그에 대응하는 스크린샷을 선택
            view_files = [f for f in os.listdir(view_hierarchies_path) if f.endswith('.json')]
            if not view_files:
                continue

            view_file = random.choice(view_files)
            screenshot_file = view_file.replace('.json', '.jpg')  # 뷰 하이어라키와 동일한 이름의 스크린샷 파일 찾기
            screenshot_src_path = os.path.join(screenshots_path, screenshot_file)
            if os.path.exists(screenshot_src_path):
                # 앱 이름의 폴더 생성
                app_output_dir = os.path.join(output_dir, app_name)
                trace_output_dir = os.path.join(app_output_dir, 'trace_0')  # trace_0 폴더 생성
                view_output_dir = os.path.join(trace_output_dir, 'view_hierarchies')
                screenshot_output_dir = os.path.join(trace_output_dir, 'screenshots')

                # trace_0, view_hierarchies와 screenshots 폴더 생성
                os.makedirs(view_output_dir, exist_ok=True)
                os.makedirs(screenshot_output_dir, exist_ok=True)

                # 뷰 하이어라키 파일 복사
                src_view_hierarchy = os.path.join(view_hierarchies_path, view_file)
                dest_view_hierarchy = os.path.join(view_output_dir, view_file)
                shutil.copy2(src_view_hierarchy, dest_view_hierarchy)

                # 스크린샷 파일 복사
                dest_screenshot = os.path.join(screenshot_output_dir, screenshot_file)
                shutil.copy2(screenshot_src_path, dest_screenshot)

                selected_apps.add(app_name)  # 선택된 앱을 기록
                selected_ui_files += 1

    if selected_ui_files < num_samples:
        print(f"Warning: Only {selected_ui_files} UI files were copied due to limited valid apps.")

# 메인 함수
def main():
    dataset_root = 'ricodataset\filtered_traces'  # filtered_traces 폴더 경로
    error_apps_csv = 'error_apps.csv'  # 에러난 앱 목록 CSV 파일 경로
    output_dir = 'ricodataset\negativefolderexample\filtered_traces'  # 복사할 파일 저장할 폴더 경로

    # 에러난 앱들을 로드
    error_apps = load_error_apps(error_apps_csv)
    print(f"Error apps loaded: {len(error_apps)}")

    # 유효한 앱 목록 필터링
    valid_apps = filter_valid_apps(dataset_root, error_apps)
    print(f"Valid apps available: {len(valid_apps)}")

    # 무작위로 50개의 UI 뷰 하이어라키와 스크린샷을 복사
    copy_random_ui_files(valid_apps, output_dir, num_samples=100)
    print(f"Successfully copied 100 random UI files to {output_dir}")

if __name__ == "__main__":
    main()
