import { PointerEvent, useCallback, useEffect, useRef, useState } from "react";

type AvatarCropModalProps = {
  imageFile: File;
  onCancel: () => void;
  onConfirm: (blob: Blob) => void | Promise<void>;
  confirming?: boolean;
};

const OUTPUT_SIZE = 256;

function coverScale(imageWidth: number, imageHeight: number, frameSize: number): number {
  return Math.max(frameSize / imageWidth, frameSize / imageHeight);
}

async function cropToCircularBlob(
  image: HTMLImageElement,
  options: {
    zoom: number;
    offsetX: number;
    offsetY: number;
    frameSize: number;
  },
): Promise<Blob> {
  const { zoom, offsetX, offsetY, frameSize } = options;
  const canvas = document.createElement("canvas");
  canvas.width = OUTPUT_SIZE;
  canvas.height = OUTPUT_SIZE;
  const ctx = canvas.getContext("2d");
  if (!ctx) {
    throw new Error("Unable to create canvas context.");
  }

  const base = coverScale(image.naturalWidth, image.naturalHeight, frameSize);
  const scale = (OUTPUT_SIZE / frameSize) * base * zoom;
  const drawWidth = image.naturalWidth * scale;
  const drawHeight = image.naturalHeight * scale;
  const dx = OUTPUT_SIZE / 2 + offsetX * (OUTPUT_SIZE / frameSize) - drawWidth / 2;
  const dy = OUTPUT_SIZE / 2 + offsetY * (OUTPUT_SIZE / frameSize) - drawHeight / 2;

  ctx.clearRect(0, 0, OUTPUT_SIZE, OUTPUT_SIZE);
  ctx.beginPath();
  ctx.arc(OUTPUT_SIZE / 2, OUTPUT_SIZE / 2, OUTPUT_SIZE / 2, 0, Math.PI * 2);
  ctx.closePath();
  ctx.clip();
  ctx.drawImage(image, dx, dy, drawWidth, drawHeight);

  return new Promise((resolve, reject) => {
    canvas.toBlob((blob) => {
      if (!blob) {
        reject(new Error("Unable to export cropped image."));
        return;
      }
      resolve(blob);
    }, "image/png");
  });
}

function loadImageElement(src: string): Promise<HTMLImageElement> {
  return new Promise((resolve, reject) => {
    const image = new Image();
    image.onload = () => resolve(image);
    image.onerror = () => reject(new Error("Unable to load the selected image."));
    image.src = src;
  });
}

function readFileAsDataUrl(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => {
      if (typeof reader.result === "string") {
        resolve(reader.result);
        return;
      }
      reject(new Error("Unable to read the selected image."));
    };
    reader.onerror = () => reject(new Error("Unable to read the selected image."));
    reader.readAsDataURL(file);
  });
}

async function decodeImageFile(file: File): Promise<{ image: HTMLImageElement; previewSrc: string }> {
  // Prefer createImageBitmap — more reliable for phone/camera JPEGs than blob: object URLs.
  if (typeof createImageBitmap === "function") {
    try {
      const bitmap = await createImageBitmap(file);
      const canvas = document.createElement("canvas");
      canvas.width = bitmap.width;
      canvas.height = bitmap.height;
      const ctx = canvas.getContext("2d");
      if (!ctx) {
        bitmap.close();
        throw new Error("Unable to create canvas context.");
      }
      ctx.drawImage(bitmap, 0, 0);
      bitmap.close();
      const previewSrc = canvas.toDataURL("image/jpeg", 0.92);
      const image = await loadImageElement(previewSrc);
      return { image, previewSrc };
    } catch {
      // Fall through to FileReader path.
    }
  }

  const previewSrc = await readFileAsDataUrl(file);
  const image = await loadImageElement(previewSrc);
  return { image, previewSrc };
}

export default function AvatarCropModal({
  imageFile,
  onCancel,
  onConfirm,
  confirming = false,
}: AvatarCropModalProps) {
  const frameRef = useRef<HTMLDivElement>(null);
  const imageRef = useRef<HTMLImageElement | null>(null);
  const [previewSrc, setPreviewSrc] = useState<string | null>(null);
  const [zoom, setZoom] = useState(1);
  const [offset, setOffset] = useState({ x: 0, y: 0 });
  const [dragging, setDragging] = useState(false);
  const dragOrigin = useRef({ x: 0, y: 0, ox: 0, oy: 0 });
  const [imageReady, setImageReady] = useState(false);
  const [naturalSize, setNaturalSize] = useState({ width: 0, height: 0 });
  const [frameSize, setFrameSize] = useState(288);
  const [error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;
    setError("");
    setImageReady(false);
    setPreviewSrc(null);
    imageRef.current = null;

    void decodeImageFile(imageFile)
      .then(({ image, previewSrc: nextPreview }) => {
        if (cancelled) {
          return;
        }
        imageRef.current = image;
        setNaturalSize({ width: image.naturalWidth, height: image.naturalHeight });
        setPreviewSrc(nextPreview);
        setZoom(1);
        setOffset({ x: 0, y: 0 });
        setImageReady(true);
      })
      .catch((loadError) => {
        if (cancelled) {
          return;
        }
        setError(loadError instanceof Error ? loadError.message : "Unable to load the selected image.");
      });

    return () => {
      cancelled = true;
    };
  }, [imageFile]);

  useEffect(() => {
    const frame = frameRef.current;
    if (!frame) {
      return;
    }
    const update = () => setFrameSize(frame.clientWidth || 288);
    update();
    const observer = new ResizeObserver(update);
    observer.observe(frame);
    return () => observer.disconnect();
  }, [imageReady]);

  const handlePointerDown = useCallback(
    (event: PointerEvent<HTMLDivElement>) => {
      event.currentTarget.setPointerCapture(event.pointerId);
      setDragging(true);
      dragOrigin.current = { x: event.clientX, y: event.clientY, ox: offset.x, oy: offset.y };
    },
    [offset.x, offset.y],
  );

  const handlePointerMove = useCallback(
    (event: PointerEvent<HTMLDivElement>) => {
      if (!dragging) {
        return;
      }
      setOffset({
        x: dragOrigin.current.ox + (event.clientX - dragOrigin.current.x),
        y: dragOrigin.current.oy + (event.clientY - dragOrigin.current.y),
      });
    },
    [dragging],
  );

  const handlePointerUp = useCallback((event: PointerEvent<HTMLDivElement>) => {
    if (event.currentTarget.hasPointerCapture(event.pointerId)) {
      event.currentTarget.releasePointerCapture(event.pointerId);
    }
    setDragging(false);
  }, []);

  async function handleConfirm() {
    const image = imageRef.current;
    const frame = frameRef.current;
    if (!image || !frame) {
      return;
    }
    setError("");
    try {
      const blob = await cropToCircularBlob(image, {
        zoom,
        offsetX: offset.x,
        offsetY: offset.y,
        frameSize: frame.clientWidth,
      });
      await onConfirm(blob);
    } catch (cropError) {
      setError(cropError instanceof Error ? cropError.message : "Unable to crop image.");
    }
  }

  const base =
    naturalSize.width > 0 && naturalSize.height > 0
      ? coverScale(naturalSize.width, naturalSize.height, frameSize)
      : 1;
  const previewWidth = naturalSize.width * base * zoom;
  const previewHeight = naturalSize.height * base * zoom;
  const previewTransform = `translate(-50%, -50%) translate(${offset.x}px, ${offset.y}px)`;

  return (
    <div className="avatar-crop-modal-backdrop" role="presentation" onClick={onCancel}>
      <div
        className="avatar-crop-modal"
        role="dialog"
        aria-modal="true"
        aria-labelledby="avatar-crop-title"
        onClick={(event) => event.stopPropagation()}
      >
        <header className="avatar-crop-modal-header">
          <h3 id="avatar-crop-title">Frame your headshot</h3>
          <p className="muted">Drag to center, then zoom to fill the circle.</p>
        </header>

        <div
          ref={frameRef}
          className={`avatar-crop-frame${dragging ? " avatar-crop-frame-dragging" : ""}`}
          onPointerDown={handlePointerDown}
          onPointerMove={handlePointerMove}
          onPointerUp={handlePointerUp}
          onPointerCancel={handlePointerUp}
        >
          {imageReady && previewSrc ? (
            <img
              src={previewSrc}
              alt=""
              className="avatar-crop-image"
              style={{
                width: `${previewWidth}px`,
                height: `${previewHeight}px`,
                transform: previewTransform,
              }}
              draggable={false}
            />
          ) : null}
          <div className="avatar-crop-mask" aria-hidden="true" />
        </div>

        <label className="avatar-crop-zoom">
          Zoom
          <input
            type="range"
            min={1}
            max={3}
            step={0.05}
            value={zoom}
            onChange={(event) => setZoom(Number(event.target.value))}
            disabled={!imageReady || confirming}
          />
        </label>

        {error ? <p className="status error">{error}</p> : null}

        <div className="avatar-crop-actions">
          <button type="button" className="secondary-button" onClick={onCancel} disabled={confirming}>
            Cancel
          </button>
          <button type="button" onClick={() => void handleConfirm()} disabled={!imageReady || confirming}>
            {confirming ? "Saving…" : "Save headshot"}
          </button>
        </div>
      </div>
    </div>
  );
}
