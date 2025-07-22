import cv2
import numpy as np

def preprocess_image(input_path, output_path):
    img = cv2.imread(input_path)
    if img is None:
        raise ValueError(f"Could not load image: {input_path}")

    # 1. Denoising
    img = cv2.fastNlMeansDenoisingColored(img, None, 10, 10, 7, 21)

    # 2. Simple white balance (gray world)
    result = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
    avg_a = np.average(result[:, :, 1].astype(np.float32))
    avg_b = np.average(result[:, :, 2].astype(np.float32))
    result[:, :, 1] = result[:, :, 1] - ((avg_a - 128) * (result[:, :, 0] / 255.0) * 1.1)
    result[:, :, 2] = result[:, :, 2] - ((avg_b - 128) * (result[:, :, 0] / 255.0) * 1.1)
    img = cv2.cvtColor(result, cv2.COLOR_LAB2BGR)

    # 3. Histogram equalization (on luminance channel)
    img_yuv = cv2.cvtColor(img, cv2.COLOR_BGR2YUV)
    img_yuv[:,:,0] = cv2.equalizeHist(img_yuv[:,:,0])
    img = cv2.cvtColor(img_yuv, cv2.COLOR_YUV2BGR)

    # 4. Center crop to square
    h, w = img.shape[:2]
    min_dim = min(h, w)
    startx = w//2 - min_dim//2
    starty = h//2 - min_dim//2
    img = img[starty:starty+min_dim, startx:startx+min_dim]

    # 5. Resize to CLIP-friendly size for much faster embedding!
    TARGET_SIZE = 512  # or 384 or 224 for even faster
    img = cv2.resize(img, (TARGET_SIZE, TARGET_SIZE), interpolation=cv2.INTER_AREA)

    cv2.imwrite(output_path, img)
    return output_path
