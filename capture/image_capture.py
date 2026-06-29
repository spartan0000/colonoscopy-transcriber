import cv2
import os
import time
import pathlib
import requests

from dotenv import load_dotenv
load_dotenv()


OUTPUT_FOLDER = "captured_images"
BASE_URL = os.getenv('API_BASE_URL')


def save_frame_locally(frame, output_folder, timestamp):
    """save frame to local file system and returns filename"""

    os.makedirs(output_folder, exist_ok=True)
    filename = os.path.join(output_folder, f"endoscope_{timestamp}.png")
    cv2.imwrite(filename, frame)
    return filename

def upload_image(filename, transcript_id):
    with open(filename, 'rb') as f:
        response = requests.post(
            f"{BASE_URL}/transcripts/{transcript_id}/images",
            files = {"image": (os.path.basename(filename), f, 'image/png')},
            data = {"captured_at":time.strftime("%Y%m%d_%H%M%S")})

        response.raise_for_status()
        return response.json()
    

def run_trigger_capture(transcript_id: int, device_index:int = 0):

    cap = cv2.VideoCapture(device_index)

    print("---Press SPACE to capture, ESC to quit---")

    while True:
        ret, frame = cap.read()
        if not ret:
            continue

        cv2.imshow("Live monitor", frame)

        key = cv2.waitKey(1) & 0xFF

        if key == 27:
            break

        elif key == 32:
            print(f"Space key detected: {key}")
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            filename = save_frame_locally(frame, OUTPUT_FOLDER, timestamp)
            cv2.imwrite(filename, frame)
            print(f"[Trigger detected] Saved image: {filename}") #images now saved locally

            try: #sending images to fastapi server
                result = upload_image(filename, transcript_id)
                print(f"Uploaded: image id: {result['image_id']}")
            except requests.RequestException as e:
                print(f"Upload failed.  Image saved locally: {e}")

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    transcript_id = int(input("enter transcript_id: "))
    run_trigger_capture(transcript_id=transcript_id)