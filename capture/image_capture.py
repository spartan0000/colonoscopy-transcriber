import cv2
import os
import time
import pathlib
import requests




def run_trigger_capture(transcript_id: int, device_index:int = 0):
    output_folder = "captured_images"

    os.makedirs(output_folder, exist_ok = True)

    cap = cv2.VideoCapture(0)

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
            filename = os.path.join(output_folder, f"endoscope_{timestamp}.png")
            cv2.imwrite(filename, frame)
            print(f"[Trigger detected] Saved image: {filename}")

            try:
                with open(filename, "rb") as f:
                    response = requests.post(
                        f"/transcripts/{transcript_id}/images",
                        files = {"image":(os.path.basename(filename), f, "image/png" )},
                        data = {"captured_at":timestamp.isoformat()}
                        )
                    response.raise_for_status()
                    print(f"Uploaded: image id: {response.json()['image_id']}")
            except requests.RequestException as e:
                print(f"Upload failed.  Image saved locally: {e}")

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    transcript_id = int(input("enter transcript_id: "))
    run_trigger_capture(transcript_id)