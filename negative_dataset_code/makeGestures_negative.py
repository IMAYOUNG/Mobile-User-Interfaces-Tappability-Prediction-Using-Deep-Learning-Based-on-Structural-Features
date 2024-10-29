import sys
import json
import os
from PyQt5.QtWidgets import QApplication, QLabel, QMainWindow, QPushButton, QFileDialog, QVBoxLayout, QWidget
from PyQt5.QtGui import QPixmap
from PyQt5.QtCore import Qt


class ImageWindow(QMainWindow):
    def __init__(self, image_path, app_folder_path, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Image Viewer")
        self.setGeometry(100, 100, 600, 400)

        # 이미지를 표시할 라벨
        self.image_label = QLabel(self)
        self.image_label.setAlignment(Qt.AlignCenter)
        self.setCentralWidget(self.image_label)

        self.image_path = image_path
        self.gesture_coords = []
        self.app_folder_path = app_folder_path

        # 이미지 로드 및 표시
        self.load_image()

    def load_image(self):
        # 이미지를 Pixmap으로 로드하고 원본 크기를 저장
        self.pixmap = QPixmap(self.image_path)
        self.image_label.setPixmap(self.pixmap)
        self.image_label.setScaledContents(True)

    # 마우스 클릭 이벤트 처리
    def mousePressEvent(self, event):
        # 이미지 영역 내에서 마우스 클릭 시 좌표 기록
        if event.button() == Qt.LeftButton:
            # QLabel의 크기를 기반으로 표시된 이미지 크기 가져오기
            label_width = self.image_label.width()
            label_height = self.image_label.height()

            # 원본 이미지 크기 가져오기
            image_width = self.pixmap.width()
            image_height = self.pixmap.height()

            # QLabel 내에서 클릭한 위치 가져오기
            x_in_label = event.pos().x()
            y_in_label = event.pos().y()

            # QLabel 크기를 기준으로 좌표를 정규화
            normalized_x = x_in_label / label_width
            normalized_y = y_in_label / label_height

            # 원본 이미지 크기에 맞춰 정규화된 좌표 조정
            actual_x = normalized_x * image_width
            actual_y = normalized_y * image_height

            # 원본 이미지 해상도(1440x2560)를 기준으로 좌표 정규화
            final_normalized_x = actual_x / image_width
            final_normalized_y = actual_y / image_height

            # 제스처 좌표 저장
            self.gesture_coords.append([final_normalized_x, final_normalized_y])

            # 파일 이름(확장자 제외)을 gestures_인덱스.json 파일의 키로 사용
            file_name = os.path.splitext(os.path.basename(self.image_path))[0]

            # 원하는 형식으로 제스처 좌표 출력
            gesture_data = {file_name: self.gesture_coords}

            # 앱 폴더에 제스처 데이터를 JSON 파일로 저장 (스크린샷 폴더가 아님)
            if self.app_folder_path:
                # 인덱스를 증가시키며 파일 이름 결정
                index = 1
                while True:
                    gesture_file_path = os.path.join(self.app_folder_path, f'gestures_{index}.json')
                    if not os.path.exists(gesture_file_path):  # 해당 파일이 존재하지 않으면 사용
                        break
                    index += 1

                # 새로 생성된 파일에 제스처 데이터를 저장
                with open(gesture_file_path, 'w') as file:
                    json.dump(gesture_data, file, indent=4)

                print(f"제스처 데이터가 저장되었습니다: {gesture_file_path}")

            else:
                print("오류: 앱 폴더 경로를 찾을 수 없습니다")

            # 제스처 저장 후 창 닫기
            self.close()


class GestureApp(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("제스처 주석 도구")
        self.setGeometry(100, 100, 600, 400)

        # 중앙 위젯과 레이아웃 설정
        self.central_widget = QWidget(self)
        self.layout = QVBoxLayout(self.central_widget)
        self.setCentralWidget(self.central_widget)

        # 이미지 로드 버튼
        self.load_button = QPushButton("이미지 로드", self)
        self.load_button.clicked.connect(self.load_image)
        self.layout.addWidget(self.load_button)

        # 변수 초기화
        self.image_path = None
        self.app_folder_path = None  # 앱 폴더 경로를 저장할 변수

    def load_image(self):
        # 파일 대화 상자를 열어 이미지를 선택
        file_dialog = QFileDialog(self)
        file_path, _ = file_dialog.getOpenFileName(self, "이미지 열기", "", "Image Files (*.png *.jpg *.bmp)")
        if file_path:
            self.image_path = file_path

            # 앱 폴더 경로 추출 (이미지 폴더의 상위 폴더)
            self.app_folder_path = os.path.dirname(os.path.dirname(self.image_path))
            print(f"앱 폴더 경로: {self.app_folder_path}")

            # 이미지용 새 창 열기
            self.open_image_window()

    def open_image_window(self):
        if self.image_path and self.app_folder_path:
            # 새로운 이미지 창을 생성하고 이미지를 표시
            self.image_window = ImageWindow(self.image_path, self.app_folder_path, self)
            self.image_window.show()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = GestureApp()
    window.show()
    sys.exit(app.exec_())
