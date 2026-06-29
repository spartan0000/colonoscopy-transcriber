import pytest
from unittest.mock import patch, AsyncMock, MagicMock, mock_open

import numpy as np

from capture.image_capture import run_trigger_capture, upload_image, save_frame_locally

def test_save_frame_locally(tmp_path, fake_frame):
    with patch("capture.image_capture.os.makedirs"),\
            patch("capture.image_capture.cv2.imwrite", return_value = True):
        filename = save_frame_locally(fake_frame, str(tmp_path), "20260101_120000") #fake frame, tmppath is the output folder, string for the time stamp
        assert filename.endswith("endoscope_20260101_120000.png")

def test_save_frame_locally_creates_directory(tmp_path, fake_frame):
    with patch("capture.image_capture.os.makedirs") as mock_makedirs,\
        patch("capture.image_capture.cv2.imwrite", return_value = True):

        save_frame_locally(fake_frame, str(tmp_path), "20260101_120000")

        mock_makedirs.assert_called_once_with(str(tmp_path), exist_ok = True)

def test_capture_upload_image_space_key(tmp_path):
    fake_frame = np.zeros((480,640,3), dtype = np.uint8)

    mock_cap = MagicMock()
    mock_cap.read.return_value = (True, fake_frame)

    #simulate image capture

    with patch("capture.image_capture.cv2.VideoCapture", return_value = mock_cap),\
        patch("capture.image_capture.cv2.imshow"), \
        patch("capture.image_capture.cv2.waitKey", side_effect = [32,27]), \
        patch("capture.image_capture.cv2.imwrite", return_value = True), \
        patch("builtins.open", mock_open(read_data = b'fake_image_bytes')), \
        patch("capture.image_capture.cv2.destroyAllWindows"), \
        patch("capture.image_capture.requests.post") as mock_post, \
        patch("capture.image_capture.os.makedirs"):

        mock_post.return_value.status_code = 200 #response.status_code mock
        mock_post.return_value.raise_for_status = MagicMock() #response.raise_for_status - does nothing here
        mock_post.return_value.json.return_value = {'image_id': 'test-image-123'}

        run_trigger_capture(transcript_id = 1)

        mock_post.assert_called_once()

        call_args = mock_post.call_args

        assert str(call_args.kwargs['files']['image'][0]).endswith('png')

        assert 'captured_at' in call_args.kwargs['data']