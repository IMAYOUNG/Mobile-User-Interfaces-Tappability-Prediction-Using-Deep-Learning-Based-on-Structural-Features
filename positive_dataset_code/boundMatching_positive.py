import os
import csv
import json
from tqdm import tqdm

def load_json(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            return json.load(file)
    except Exception as e:
        print(f"\nError loading {file_path}: {e}")
        return None

def load_gestures(trace_directory):
    return load_json(os.path.join(trace_directory, 'gestures.json'))

def load_view_hierarchies(view_hierarchies_path):
    view_files = {}
    total_UIs = 0  # 각 view_hierarchies 폴더 안의 UI 파일 갯수 (JSON 파일)
    if os.path.exists(view_hierarchies_path):
        for file_name in os.listdir(view_hierarchies_path):
            if file_name.endswith('.json'):
                file_path = os.path.join(view_hierarchies_path, file_name)
                # Load each view hierarchy file
                view_files[file_name] = load_json(file_path)
                total_UIs += 1  # JSON 파일 하나당 UI로 간주
    return view_files, total_UIs

def convert_coordinates(gesture_data, screen_width=1440, screen_height=2560, log_writer=None):
    converted_data = {}
    skipped_gestures = 0

    for gesture_id, coordinates in gesture_data.items():
        if not coordinates:
            skipped_gestures += 1
            log_writer.writerow([gesture_id, 'No coordinates found (possibly a scroll gesture)'])
            continue
        elif len(coordinates) > 1:
            skipped_gestures += 1
            log_writer.writerow([gesture_id, 'More than one coordinate found (possibly a scroll gesture)'])
            continue
        
        converted_data[gesture_id] = [{'x': coord[0] * screen_width, 'y': coord[1] * screen_height} for coord in coordinates]

    return converted_data, skipped_gestures

def is_within_bounds(x, y, bounds):
    left, top, right, bottom = map(int, bounds)
    return left <= x <= right and top <= y <= bottom

def is_within_rel_bounds(x, y, rel_bounds, parent_bounds):
    if not parent_bounds or len(rel_bounds) != 4:
        return False

    parent_left, parent_top, parent_right, parent_bottom = map(int, parent_bounds)
    abs_left = parent_left + (parent_right - parent_left) * rel_bounds[0]
    abs_top = parent_top + (parent_bottom - parent_top) * rel_bounds[1]
    abs_right = parent_left + (parent_right - parent_left) * rel_bounds[2]
    abs_bottom = parent_top + (parent_bottom - parent_top) * rel_bounds[3]

    return is_within_bounds(x, y, [abs_left, abs_top, abs_right, abs_bottom])

def calculate_bounds_area(bounds):
    if len(bounds) == 4:
        left, top, right, bottom = bounds
        return (right - left) * (bottom - top)
    return float('inf')
    
def calculate_hierarchy_depth(component):
    # 컴포넌트가 None이거나 자식 노드가 없으면 깊이는 1
    if component is None or 'children' not in component or not component['children']:
        return 1  # 리프 노드

    # 모든 자식의 깊이를 계산
    child_depths = [calculate_hierarchy_depth(child) for child in component['children'] if child is not None]
    
    # 자식의 최대 깊이에 1을 더하여 반환
    return max(child_depths) + 1 if child_depths else 1


def count_components_in_ui(component):
    # 컴포넌트가 None이거나 자식 노드가 없으면 노드 수는 1
    if component is None or 'children' not in component or not component['children']:
        return 1  # 현재 노드만 존재하는 경우

    # 자식 노드의 수를 재귀적으로 계산하고, 현재 노드의 수를 포함하여 반환
    child_count = sum(count_components_in_ui(child) for child in component['children'])
    
    return 1 + child_count  # 현재 노드 + 자식 노드 수의 합


def calculate_spacing(component_info, parent_info, siblings_info):
    current_bounds = component_info.get('bounds', [])
    parent_bounds = parent_info.get('bounds', []) if parent_info else []

    # 부모 요소의 width와 height 계산
    parent_width = parent_bounds[2] - parent_bounds[0] if parent_bounds else 1  # width
    parent_height = parent_bounds[3] - parent_bounds[1] if parent_bounds else 1  # height

    # 부모 요소와의 간격 계산 후 부모 요소의 크기로 스케일링
    top_spacing = (current_bounds[1] - parent_bounds[1]) / parent_height if parent_bounds else float('inf')
    bottom_spacing = (parent_bounds[3] - current_bounds[3]) / parent_height if parent_bounds else float('inf')
    left_spacing = (current_bounds[0] - parent_bounds[0]) / parent_width if parent_bounds else float('inf')
    right_spacing = (parent_bounds[2] - current_bounds[2]) / parent_width if parent_bounds else float('inf')

    # 형제 요소들과의 간격 계산
    for sibling in siblings_info:
        sibling_bounds = sibling.get('bounds', [])
        if not sibling_bounds:
            continue

        is_overlapping_vertically = (sibling_bounds[3] > current_bounds[1] and sibling_bounds[1] < current_bounds[3])
        is_overlapping_horizontally = (sibling_bounds[2] > current_bounds[0] and sibling_bounds[0] < current_bounds[2])

        # 상단 간격 계산
        if sibling_bounds[3] < current_bounds[1] and is_overlapping_horizontally:
            top_spacing = min(top_spacing, (current_bounds[1] - sibling_bounds[3]) / parent_height)

        # 하단 간격 계산
        if sibling_bounds[1] > current_bounds[3] and is_overlapping_horizontally:
            bottom_spacing = min(bottom_spacing, (sibling_bounds[1] - current_bounds[3]) / parent_height)

        # 좌측 간격 계산
        if sibling_bounds[2] < current_bounds[0] and is_overlapping_vertically:
            left_spacing = min(left_spacing, (current_bounds[0] - sibling_bounds[2]) / parent_width)

        # 우측 간격 계산
        if sibling_bounds[0] > current_bounds[2] and is_overlapping_vertically:
            right_spacing = min(right_spacing, (sibling_bounds[0] - current_bounds[2]) / parent_width)

    return {
        'top_spacing': top_spacing,
        'bottom_spacing': bottom_spacing,
        'left_spacing': left_spacing,
        'right_spacing': right_spacing
    }

def recursive_search(parent, component, x, y, depth, ancestors):
    # component가 None일 경우 탐색을 중단
    if component is None:
        return []

    matched_components = []
    bounds = component.get('bounds', [])
    rel_bounds = component.get('rel-bounds', [])

    if (is_within_bounds(x, y, bounds) or is_within_rel_bounds(x, y, rel_bounds, parent.get('bounds', []) if parent else [])):
        children = component.get('children', [])
        current_ancestors = ancestors[:]  
        current_ancestors.append(component.get('class', 'Unknown'))

        if children:
            for child in children:
                matched_components.extend(recursive_search(component, child, x, y, depth + 1, current_ancestors))
        else:
            # parent가 None일 경우 빈 리스트로 설정
            sibling_count = len(parent.get('children', [])) if parent else 0
            sibling_classes = [sib.get('class', 'Unknown') for sib in parent.get('children', [])] if parent else []

            # 부모 아래에 있는 모든 컴포넌트들의 갯수와 종류 리스트 추가
            parent_components_count = len(parent.get('children', [])) if parent else 0
            parent_component_classes = [child.get('class', 'Unknown') for child in parent.get('children', [])] if parent else []

            hierarchy_depth = calculate_hierarchy_depth(parent)

            component_info = {
                'class': component.get('class', 'Unknown'),
                'bounds': bounds,
                'siblings': sibling_count,
                'siblings_classes': sibling_classes,
                'parent_components_count': parent_components_count,  # 부모 아래 컴포넌트 갯수
                'parent_component_classes': parent_component_classes,  # 부모 아래 컴포넌트 종류 리스트
                'Hierarchy_Depth': hierarchy_depth,  
                'Nesting_Level': depth,  
                'ancestors': current_ancestors,
                'ancestors_cnt': len(current_ancestors),
                'parent_node': parent  # 부모 노드 저장
            }
            matched_components.append((component, component_info))

    return matched_components

def get_direct_child_components_info(parent_component):
    # 부모 컴포넌트 아래에 있는 모든 자식 컴포넌트의 수와 종류를 계산하는 함수
    if parent_component is None or 'children' not in parent_component:
        return 0, []

    direct_child_count = len(parent_component['children'])
    direct_child_classes = [child.get('class', 'Unknown') for child in parent_component['children']]

    return direct_child_count, direct_child_classes

def get_all_descendant_components_info(parent_component):
    # 부모 컴포넌트 아래에 있는 모든 자식 및 하위 자식 컴포넌트의 수와 종류를 계산하는 함수
    if parent_component is None or 'children' not in parent_component:
        return 0, []

    descendant_count = 0
    descendant_classes = []

    def traverse_descendants(component):
        nonlocal descendant_count, descendant_classes
        if component and 'children' in component:  # 컴포넌트가 None이 아닌지 확인
            for child in component['children']:
                if child:  # 자식 컴포넌트가 None이 아닌지 확인
                    descendant_count += 1
                    descendant_classes.append(child.get('class', 'Unknown'))
                    traverse_descendants(child)  # 재귀적으로 모든 하위 자식 탐색

    traverse_descendants(parent_component)
    return descendant_count, descendant_classes



def find_matching_components(converted_gestures, view_hierarchies, log_writer):
    matched_gestures = []
    recorded_gestures = set()
    matched_components_count = 0
    skipped_hierarchies_count = 0

    for gesture_id, gestures in converted_gestures.items():
        if gesture_id in recorded_gestures:
            continue

        view_hierarchy_file = f"{gesture_id}.json"
        view_hierarchy = view_hierarchies.get(view_hierarchy_file)

        if view_hierarchy is None:
            log_writer.writerow([gesture_id, f'No view hierarchy found or invalid JSON for {view_hierarchy_file}'])
            skipped_hierarchies_count += 1
            continue

        root_component = view_hierarchy.get('activity', {}).get('root', {})
        if not root_component:
            log_writer.writerow([gesture_id, f'Empty or invalid view hierarchy for {view_hierarchy_file}'])
            skipped_hierarchies_count += 1
            continue

        # 전체 트리의 깊이 계산
        overall_hierarchy_depth = calculate_hierarchy_depth(root_component)

        # UI당 컴포넌트 수 계산
        total_components_in_ui = count_components_in_ui(root_component)

        matched = False  # 매칭 여부를 확인하기 위한 변수

        for gesture in gestures:
            x, y = gesture['x'], gesture['y']
            try:
                matching_components = recursive_search(None, root_component, x, y, 0, [])
            except AttributeError as e:
                log_writer.writerow([gesture_id, f'Error: {e} in {view_hierarchy_file}'])
                continue

            if matching_components:
                component, component_info = sorted(matching_components, key=lambda x: (x[1]['Hierarchy_Depth'], x[1]['Nesting_Level']), reverse=True)[0]

                parent_info = component_info.get('parent_node', None)  # 매칭된 노드의 부모 정보를 가져옵니다.

                if parent_info:
                    descendant_count, descendant_classes = get_all_descendant_components_info(parent_info)
                else:
                    descendant_count, descendant_classes = 0, []


                siblings_info = [sibling for sibling in parent_info.get('children', []) if sibling != component] if parent_info else []

                spacing_info = calculate_spacing(component_info, parent_info, siblings_info)

                matched_gestures.append({
                    'UI': gesture_id,
                    'gesture_converted': [x, y],
                    'component_info': {
                        'bounds': component.get('bounds', []),
                        'class': component.get('class', 'Unknown'),
                        'ancestors': component_info['ancestors'],
                        'ancestors_cnt': component_info['ancestors_cnt'],
                        'siblings': component_info['siblings_classes'],
                        'siblings_cnt': component_info['siblings'],
                        'Hierarchy_Depth': overall_hierarchy_depth,
                        'Nesting_Level': component_info['Nesting_Level'],
                        'clickable': component.get('clickable', 'false'),
                        'spacing': spacing_info,
                        'total_components_in_ui': total_components_in_ui,  # UI당 컴포넌트 수 추가
                        'descendant_count': descendant_count,  # 직계 부모 아래 하위 노드의 수
                        'descendant_classes': descendant_classes  # 직계 부모 아래 하위 노드의 종류 리스트
                    }
                })


                recorded_gestures.add(gesture_id)
                matched_components_count += 1
                matched = True  # 매칭된 경우
                break

        if not matched:
            log_writer.writerow([gesture_id, f'Did not match any component in {view_hierarchy_file}'])

    return matched_gestures, matched_components_count, skipped_hierarchies_count

def save_to_json(data, output_file):
    print(f"Saving {len(data)} entries to {output_file}")  # 데이터 갯수 확인
    with open(output_file, 'w', encoding='utf-8') as file:
        json.dump(data, file, indent=4, ensure_ascii=False)

def process_trace_data(trace_directory, app_name, log_writer):
    gesture_data = load_gestures(trace_directory)

    converted_gestures, skipped_gestures = convert_coordinates(gesture_data, log_writer=log_writer)
    view_hierarchies_path = os.path.join(trace_directory, 'view_hierarchies')
    view_files, total_UIs = load_view_hierarchies(view_hierarchies_path)
    
    total_view_hierarchies = 1 if os.path.exists(view_hierarchies_path) else 0

    matched_gestures, matched_components_count, skipped_hierarchies_count = find_matching_components(converted_gestures, view_files, log_writer)
    
    return matched_gestures, matched_components_count, skipped_gestures, skipped_hierarchies_count, total_view_hierarchies, total_UIs, skipped_hierarchies_count

def process_single_app_traces(dataset_root, app_name, log_writer, max_traces=None):
    app_directory = os.path.join(dataset_root, 'filtered_traces', app_name)
    trace_folders = [d for d in os.listdir(app_directory) if os.path.isdir(os.path.join(app_directory, d))]

    if max_traces:
        trace_folders = trace_folders[:max_traces]

    app_data = {"app_name": app_name, "traces": {}} 
    total_skipped_gestures, total_components, total_skip_hierarchies, total_view_hierarchies, total_UIs, total_skipped_UIs = 0, 0, 0, 0, 0, 0  

    for trace_name in tqdm(trace_folders, desc=f"Processing traces for {app_name}", leave=False):
        trace_directory = os.path.join(app_directory, trace_name)
        matched_gestures, matched_components_count, skipped_gestures, skipped_hierarchies_count, view_hierarchies_count, app_total_UIs, app_skipped_UIs = process_trace_data(trace_directory, app_name, log_writer)

        # 앱의 제스처가 없거나 UI가 없으면 None file로 기록
        if matched_gestures:
            app_data["traces"][trace_name] = matched_gestures
        else:
            app_data["traces"][trace_name] = "None file"  # None file 기록

        total_skipped_gestures += skipped_gestures
        total_components += matched_components_count
        total_skip_hierarchies += skipped_hierarchies_count
        total_view_hierarchies += view_hierarchies_count  # view hierarchies 폴더의 갯수
        total_UIs += app_total_UIs  # 각 view hierarchies 폴더 안의 UI 파일 갯수 (JSON 파일)
        total_skipped_UIs += app_skipped_UIs

    return app_data, total_skipped_gestures, total_components, total_skip_hierarchies, total_view_hierarchies, total_UIs, total_skipped_UIs

def main():
    dataset_root = r''  # Set your root path
    app_names = [d for d in os.listdir(os.path.join(dataset_root, 'filtered_traces')) if os.path.isdir(os.path.join(dataset_root, 'filtered_traces', d))]

    total_apps = len(app_names)

    all_app_data = []
    total_skipped_gestures, total_components, total_skip_hierarchies, total_view_hierarchies, total_UIs, total_skipped_UIs = 0, 0, 0, 0, 0, 0  

    # Open CSV file to log skipped gestures and hierarchies
    with open('skipped_log.csv', 'w', newline='', encoding='utf-8') as log_file:
        log_writer = csv.writer(log_file)
        log_writer.writerow(['Gesture ID', 'Reason'])  # CSV 헤더 작성

        with tqdm(total=total_apps, desc="Processing apps") as pbar:
            for app_name in app_names:
                app_data, skipped_gestures, app_total_components, app_skip_hierarchies, app_view_hierarchies, app_total_UIs, app_skipped_UIs = process_single_app_traces(dataset_root, app_name, log_writer)
                all_app_data.append(app_data)
                total_skipped_gestures += skipped_gestures
                total_components += app_total_components
                total_skip_hierarchies += app_skip_hierarchies
                total_view_hierarchies += app_view_hierarchies
                total_UIs += app_total_UIs
                total_skipped_UIs += app_skipped_UIs
                
                pbar.update(1)

    save_to_json(all_app_data, 'dataset/matching_output.json')

    # Summary information
    print(f"Total apps: {total_apps}") # 총 앱의 갯수
    print(f"Total UIs: {total_UIs}") # 총 UI의 갯수 (view hierarchies 폴더 안 JSON 파일)
    print("--------------------------------------------------------------------")    
    print(f"Total components processed: {total_components}")
    print(f"Matching Apps: {len([app for app in all_app_data if app['traces']])}")

if __name__ == "__main__":
    main()
