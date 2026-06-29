import pytest
from unittest.mock import patch, AsyncMock, MagicMock, mock_open

import numpy as np
import requests

from capture.image_capture import run_trigger_capture, upload_image, save_frame_locally

#tests save local functionality
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

def test_save_frame_locally_calls_imwrite(tmp_path, fake_frame):
    with patch("capture.image_capture.os.makedirs"),\
        patch("capture.image_capture.cv2.imwrite") as mock_imwrite:

        save_frame_locally(fake_frame, str(tmp_path), "20260101_120000")

        mock_imwrite.assert_called_once()

#tests upload image functionality

def test_upload_image_success(tmp_path):
    filename = str(tmp_path / "endoscope_20260101_120000.png")
    mock_response = MagicMock()
    mock_response.json.return_value = {'image_id': 'test-image-123'}
    mock_response.raise_for_status = MagicMock() #basically a success scenario guaranteed for this test

    with patch("capture.image_capture.requests.post", return_value = mock_response) as mock_post,\
        patch("builtins.open", mock_open(read_data = b'fake_image_bytes')):

        result = upload_image(filename, transcript_id = 1) #the requested endpoint returns image_id

        assert result['image_id'] == 'test-image-123'

        mock_post.assert_called_once()

        assert '/transcripts/1/images' in mock_post.call_args.args[0] 
        args, kwargs = mock_post.call_args

        assert kwargs['data']['captured_at'] is not None
        filename_in_request =  kwargs['files']['image'][0]
        assert "endoscope_20260101_120000" in filename_in_request

def test_upload_images_raises_on_failure(tmp_path):
    filename = str(tmp_path / "endoscope_20260101_120000")

    mock_response = MagicMock()
    mock_response.raise_for_status.side_effect = requests.RequestException("Server error")

    with patch("capture.image_capture.requests.post", return_value = mock_response),\
        patch('builtins.open', mock_open(read_data=b'fake_image_bytes')):

        with pytest.raises(requests.RequestException):
            upload_image(filename, transcript_id = 1)

def test_run_trigger_image_capture_space_then_esc(mock_cap):
    """space key captures and uploads, esc quits"""

    with patch("capture.image_capture.cv2.VideoCapture", return_value=mock_cap),\
        patch("capture.image_capture.cv2.imshow"),\
        patch("capture.image_capture.cv2.waitKey", side_effect =[32,27]),\
        patch("capture.image_capture.cv2.destroyAllWindows"),\
        patch("capture.image_capture.save_frame_locally", return_value = "fake_file.png") as mock_save,\
        patch("capture.image_capture.upload_image", return_value = {'image_id': 'fake-image-123'}) as mock_upload:

        run_trigger_capture(transcript_id=1)

        mock_save.assert_called_once()
        mock_upload.assert_called_once_with("fake_file.png", 1)


        
              
