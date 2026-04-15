import requests
import os
import cv2
from dotenv import load_dotenv

# Load env
load_dotenv()

API_KEY = os.getenv("FACE_API_KEY")
API_SECRET = os.getenv("FACE_API_SECRET")

IMAGE_PATH = "test.jpg"

def detect_faces(image_path):
    url = "https://api-us.faceplusplus.com/facepp/v3/detect"

    data = {
        "api_key": API_KEY,
        "api_secret": API_SECRET,
        "return_attributes": "age"
    }

    with open(image_path, "rb") as f:
        files = {"image_file": f}
        response = requests.post(url, data=data, files=files)

    return response.json()


def draw_boxes(image_path, result):
    img = cv2.imread(image_path)

    if "faces" not in result:
        print("❌ No faces found")
        return

    for face in result["faces"]:
        rect = face["face_rectangle"]
        age  = face["attributes"]["age"]["value"]

        x = rect["left"]
        y = rect["top"]
        w = rect["width"]
        h = rect["height"]

        # 🟩 Draw rectangle
        cv2.rectangle(img, (x, y), (x+w, y+h), (0, 255, 0), 2)

        # 🏷️ Put age text
        cv2.putText(img, f"Age: {age}", (x, y-10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0,255,0), 2)

    cv2.imshow("Age Detection", img)
    cv2.waitKey(0)
    cv2.destroyAllWindows()


if __name__ == "__main__":
    result = detect_faces(IMAGE_PATH)
    print(result)  # debug

    draw_boxes(IMAGE_PATH, result)