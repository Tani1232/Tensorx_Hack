import requests
import os
import tempfile
import base64

class FaceVerifier:
    def __init__(self):
        self.api_key = os.getenv("FACE_API_KEY")
        self.api_secret = os.getenv("FACE_API_SECRET")
        self.url = "https://api-us.faceplusplus.com/facepp/v3/detect"

    def verify_age(self, base64_image: str) -> int:
        if not self.api_key or not self.api_secret:
            print("❌ Face++ API keys missing. Cannot verify age.")
            return -1

        tmp_path = None

        try:
            if not isinstance(base64_image, str) or not base64_image:
                return -1

            # Strip data URI header if present
            if "," in base64_image:
                base64_image = base64_image.split(",", 1)[1]

            image_data = base64.b64decode(base64_image, validate=True)
            with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp_file:
                tmp_file.write(image_data)
                tmp_path = tmp_file.name

            data = {
                "api_key": self.api_key,
                "api_secret": self.api_secret,
                "return_attributes": "age"
            }

            with open(tmp_path, "rb") as f:
                files = {"image_file": f}
                response = requests.post(self.url, data=data, files=files, timeout=(5, 15))

            result = response.json()
            if "faces" in result and len(result["faces"]) > 0:
                age = result["faces"][0]["attributes"]["age"]["value"]
                print(f"[FACE VERIFICATION]: Detected age is {age}")
                return age
            else:
                print("❌ No faces found in captured frame")
                return -1

        except Exception as e:
            print(f"Face verification Error: {e}")
            return -1
        finally:
            if tmp_path and os.path.exists(tmp_path):
                os.remove(tmp_path)
