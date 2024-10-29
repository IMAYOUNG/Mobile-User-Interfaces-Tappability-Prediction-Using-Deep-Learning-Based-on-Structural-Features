import json
import pandas as pd
import re
import csv

# 화면 해상도 정보 
screen_width = 1440
screen_height = 2560

# 키워드 목록을 분류 유형별로 사전에 저장
component_keywords = {
    'Advertisement': ['adview', 'htmlbannerwebview', 'adcontainer'],
    'BottomNavigation': ['bottomtabgroupview', 'bottombar'],
    'ButtonBar': ['buttonbar'],
    'Card': ['cardview'],
    'Checkbox': ['checkbox', 'checkedtextview', 'appcompatcheckedtextview', 'appcompatcheckbox'],
    'Drawer': ['DrawerLayout'],
    'DatePicker': ['datepicker'],
    'Input': ['edittext', 'searchboxview', 'appcompatautocompletetextview', 'autocompletetextview', 'appcompatedittext'],
    'ListItem': ['listView','recyclerview', 'listpopupwindow', 'tabitem', 'gridview'], 
    'MapView': ['mapview'],
    'MultiTab': ['slidingtab'],
    'NumberStepper': ['numberpicker'],
    'OnOffSwitch': ['switch'],
    'PageIndicator': ['viewpagerindicatordots', 'pageindicator', 'circleindicator', 'pagerindicator'],
    'RadioButton': ['radiobutton','appcompatradiobutton'],
    'Slider': ['seekbar'],
    'Toolbar': ['toolbar', 'titlebar', 'actionbar'],
    'Video': ['videoview'],
    'WebView': ['webview'],
    'TextButton': ['button', 'textview', 'appcompattextview'],
    'Image': ['imageview', 'appcompatimageview', 'imagebutton', 'glyphview', 'appcompatbutton', 'appcompatimagebutton', 'actionmenuitemview', 'actionmenuitempresenter']
}

# 클래스명을 마지막 두 부분만 추출하여 반환하는 함수
def extract_base_class(class_name):
    parts = class_name.lower().split('.')  # 소문자로 변환하여 분리
    return parts[-2:] if len(parts) > 1 else parts

# 클래스명을 기준으로 정확한 단어 매칭을 통해 다양한 UI 컴포넌트로 분류하고, Other로 분류된 경우 기록하는 함수
def classify_component_class(app_name, ui_name, class_name, other_classes_writer):
    base_class_parts = extract_base_class(class_name)
    matched_type = 'Other'  # 기본 분류는 'Other'로 설정

    # 각 키워드 리스트를 순회하며 클래스명을 분류
    for part in base_class_parts:  # 두 단어 각각에 대해 비교
        for component_type, keywords in component_keywords.items():
            if part in keywords:  # 정확하게 일치하는 경우에만 해당 분류로 설정
                matched_type = component_type
                break  # 일치하는 분류를 찾으면 루프 종료
        if matched_type != 'Other':  # 이미 분류된 경우 더 이상 검사하지 않음
            break

    # Other로 분류된 경우 CSV 파일에 기록
    if matched_type == 'Other':
        other_classes_writer.writerow([app_name, ui_name, class_name])

    return matched_type

# Other로 분류된 클래스명을 CSV 파일에 저장하기 위한 함수
def process_classes(app_name, ui_name, class_list, other_classes_writer):
    classified_classes = []
    for class_name in class_list:
        classified_class = classify_component_class(app_name, ui_name, class_name, other_classes_writer)
        classified_classes.append(classified_class)
    return classified_classes

# 중복 확인을 위한 기록된 UI-클래스 쌍 저장용 set
recorded_ui_classes = set()

# JSON 파일 로드 및 데이터 처리
def process_data_from_json(json_file, other_classes_filepath='other_classes.csv', classified_data_filepath=r'C:\Users\USER\Desktop\Code\sitlab\0731\classified_data_100.csv'):
    with open(other_classes_filepath, mode='w', newline='', encoding='utf-8') as file:
        other_classes_writer = csv.writer(file)
        other_classes_writer.writerow(['App', 'UI', 'Class'])  # CSV 헤더 추가

        with open(json_file, 'r', encoding='utf-8') as file:
            data = json.load(file)

        # 데이터 추출 및 정리
        rows = []
        for entry in data:
            app_name = entry['app_name']
            traces = entry['traces']
            
            for trace_name, gestures in traces.items():
                if isinstance(gestures, list):  
                    for gesture in gestures:
                        ui = gesture.get("UI")  # get() 메서드 사용으로 키가 없는 경우를 대비
                        gesture_x, gesture_y = gesture["gesture_converted"]
                        component_info = gesture["component_info"]
                        bounds = component_info["bounds"]
                        component_class = component_info["class"]
                        total_components = component_info["total_components_in_ui"]
                        descendant_count = component_info["descendant_count"]
                        descendant_classes = component_info["descendant_classes"]
                        
                                                # descendant_classes도 키워드 목록을 사용하여 변환
                        classified_descendant_classes = process_classes(app_name, ui, descendant_classes, other_classes_writer)
                        # 수정된 부분: classify_component_class 호출 시 모든 인자 전달
                        classified_class = classify_component_class(app_name, ui, component_class, other_classes_writer)
                        
                        clickable = component_info["clickable"]
                        spacing_info = component_info.get("spacing", {})
                        top_spacing = spacing_info.get('top_spacing', None)
                        bottom_spacing = spacing_info.get('bottom_spacing', None)
                        left_spacing = spacing_info.get('left_spacing', None)
                        right_spacing = spacing_info.get('right_spacing', None)
                        
                        # Hierarchy Depth와 Nesting Level 값을 가져오기
                        hierarchy_depth = component_info.get("Hierarchy_Depth", 0)  # 기본값 0
                        nesting_level = component_info.get("Nesting_Level", 0)  # 기본값 0
                        
                        ancestors = [classify_component_class(app_name, ui, a, other_classes_writer) for a in component_info.get("ancestors", [])]
                        siblings = [classify_component_class(app_name, ui, s, other_classes_writer) for s in component_info.get("siblings", [])]
                        
                        # 중복 체크를 위한 app_name, UI, 클래스명, ancestors, siblings, clickable 조합
                        ui_class_pair = (app_name, ui, component_class, tuple(ancestors), tuple(siblings), component_info["clickable"])
                        
                        # 중복된 app_name-UI-클래스명-ancestors-siblings-clickable 조합인지 확인
                        if ui_class_pair in recorded_ui_classes:
                            continue  # 이미 기록된 조합이면 건너뜀
                        
                        # 기록되지 않은 조합은 기록
                        recorded_ui_classes.add(ui_class_pair)
                        
                        rows.append({
                            'app_name': app_name,
                            'UI': ui,
                            'gesture_x': gesture_x,
                            'gesture_y': gesture_y,
                            'bounds': bounds,
                            'classified_class': classified_class,
                            'clickable': clickable,
                            'ancestors_cnt': len(ancestors),
                            'siblings_cnt': len(siblings),
                            'ancestors': ancestors,
                            'siblings': siblings,
                            'Hierarchy_Depth': hierarchy_depth,  # Hierarchy Depth 추가
                            'Nesting_Level': nesting_level,  # Nesting Level 추가
                            'top_spacing': top_spacing,  
                            'bottom_spacing': bottom_spacing,  
                            'left_spacing': left_spacing,  
                            'right_spacing': right_spacing,
                            'total_components': total_components,
                            'descendant_count': descendant_count, 
                            'descendant_classes': classified_descendant_classes,  # 변환된 descendant_classes 사용
                        })


        # DataFrame으로 변환 및 CSV 파일로 저장
        df = pd.DataFrame(rows)
        df.to_csv(classified_data_filepath, index=False, encoding='utf-8')
        print(f"CSV 파일로 변환 완료: {classified_data_filepath}")

# JSON 파일로부터 데이터 처리 호출 예제
process_data_from_json(r'C:\Users\USER\Desktop\Code\sitlab\0731\negativefinaloutput100.json')
