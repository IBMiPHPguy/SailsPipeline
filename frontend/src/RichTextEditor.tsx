import {
  useCallback,
  useEffect,
  useLayoutEffect,
  useRef,
  useState,
  type ChangeEvent,
  type MouseEvent as ReactMouseEvent,
} from "react";
import { resolveBrandLogoUrl } from "./portalBranding";

type RichTextEditorProps = {
  value: string;
  onChange: (html: string) => void;
  placeholder?: string;
  disabled?: boolean;
  minHeight?: string;
  ariaLabel?: string;
  uploadImage?: (file: File) => Promise<string>;
};

type ToolbarCommand = {
  label: string;
  title: string;
  command: string;
  value?: string;
};

type ImageOverlayBox = {
  top: number;
  left: number;
  width: number;
  height: number;
};

type ResizeCorner = "nw" | "ne" | "sw" | "se";

const FORMAT_COMMANDS: ToolbarCommand[] = [
  { label: "B", title: "Bold", command: "bold" },
  { label: "I", title: "Italic", command: "italic" },
  { label: "U", title: "Underline", command: "underline" },
];

const BLOCK_COMMANDS: ToolbarCommand[] = [
  { label: "• List", title: "Bullet list", command: "insertUnorderedList" },
  { label: "1. List", title: "Numbered list", command: "insertOrderedList" },
];

const MAX_SIGNATURE_IMAGE_BYTES = 5 * 1024 * 1024;
const DEFAULT_IMAGE_WIDTH_PX = 240;
const MIN_IMAGE_WIDTH_PX = 48;
const MAX_IMAGE_WIDTH_PX = 560;
const RESIZE_HANDLES: ResizeCorner[] = ["nw", "ne", "sw", "se"];

function normalizeEditorHtml(html: string): string {
  const trimmed = html.trim();
  if (!trimmed || trimmed === "<br>" || trimmed === "<div><br></div>") {
    return "";
  }
  return html;
}

function isEffectivelyEmpty(html: string): boolean {
  const container = document.createElement("div");
  container.innerHTML = html;
  return (container.textContent ?? "").trim() === "" && container.querySelector("img") === null;
}

function readEditorHtml(editor: HTMLDivElement): string {
  const html = normalizeEditorHtml(editor.innerHTML);
  return isEffectivelyEmpty(html) ? "" : html;
}

function clampImageWidth(width: number, editor: HTMLDivElement | null): number {
  const editorWidth = editor?.clientWidth ?? MAX_IMAGE_WIDTH_PX;
  const maxWidth = Math.min(MAX_IMAGE_WIDTH_PX, Math.max(MIN_IMAGE_WIDTH_PX, editorWidth - 8));
  return Math.max(MIN_IMAGE_WIDTH_PX, Math.min(maxWidth, width));
}

function applyImageDimensions(image: HTMLImageElement, width: number) {
  const editor = image.closest(".rich-text-editor-surface");
  const nextWidth = clampImageWidth(width, editor instanceof HTMLDivElement ? editor : null);
  const naturalWidth = image.naturalWidth || image.offsetWidth || nextWidth;
  const naturalHeight = image.naturalHeight || image.offsetHeight || nextWidth;
  const aspectRatio = naturalHeight / naturalWidth;
  const nextHeight = Math.max(1, Math.round(nextWidth * aspectRatio));

  image.style.width = `${nextWidth}px`;
  image.style.height = `${nextHeight}px`;
  image.style.maxWidth = "none";
}

export default function RichTextEditor({
  value,
  onChange,
  placeholder = "Start typing…",
  disabled = false,
  minHeight = "10rem",
  ariaLabel = "Rich text editor",
  uploadImage,
}: RichTextEditorProps) {
  const editorRef = useRef<HTMLDivElement>(null);
  const surfaceWrapRef = useRef<HTMLDivElement>(null);
  const imageInputRef = useRef<HTMLInputElement>(null);
  const skipSyncRef = useRef(false);
  const selectedImageRef = useRef<HTMLImageElement | null>(null);
  const resizingRef = useRef(false);
  const [isFocused, setIsFocused] = useState(false);
  const [imageUploading, setImageUploading] = useState(false);
  const [imageError, setImageError] = useState("");
  const [imageStatus, setImageStatus] = useState("");
  const [selectedImage, setSelectedImage] = useState<HTMLImageElement | null>(null);
  const [overlayBox, setOverlayBox] = useState<ImageOverlayBox | null>(null);

  const updateOverlayForImage = useCallback((image: HTMLImageElement | null) => {
    if (!image || !surfaceWrapRef.current) {
      setOverlayBox(null);
      return;
    }

    const wrapRect = surfaceWrapRef.current.getBoundingClientRect();
    const imageRect = image.getBoundingClientRect();
    setOverlayBox({
      top: imageRect.top - wrapRect.top + surfaceWrapRef.current.scrollTop,
      left: imageRect.left - wrapRect.left + surfaceWrapRef.current.scrollLeft,
      width: imageRect.width,
      height: imageRect.height,
    });
  }, []);

  const clearImageSelection = useCallback(() => {
    if (selectedImageRef.current) {
      selectedImageRef.current.classList.remove("rich-text-editor-image--selected");
    }
    selectedImageRef.current = null;
    setSelectedImage(null);
    setOverlayBox(null);
  }, []);

  const selectImage = useCallback(
    (image: HTMLImageElement) => {
      if (selectedImageRef.current && selectedImageRef.current !== image) {
        selectedImageRef.current.classList.remove("rich-text-editor-image--selected");
      }
      image.classList.add("rich-text-editor-image");
      image.classList.add("rich-text-editor-image--selected");
      selectedImageRef.current = image;
      setSelectedImage(image);
      updateOverlayForImage(image);
    },
    [updateOverlayForImage],
  );

  const syncEditorFromValue = useCallback(() => {
    if (skipSyncRef.current) {
      skipSyncRef.current = false;
      return;
    }

    const editor = editorRef.current;
    if (!editor || document.activeElement === editor) {
      return;
    }
    const nextHtml = value || "";
    if (editor.innerHTML !== nextHtml) {
      editor.innerHTML = nextHtml;
      clearImageSelection();
    }
  }, [clearImageSelection, value]);

  useEffect(() => {
    syncEditorFromValue();
  }, [syncEditorFromValue]);

  useLayoutEffect(() => {
    if (!selectedImage) {
      return;
    }
    updateOverlayForImage(selectedImage);
  }, [selectedImage, updateOverlayForImage, value]);

  useEffect(() => {
    if (!selectedImage) {
      return;
    }

    function handleReposition() {
      updateOverlayForImage(selectedImageRef.current);
    }

    window.addEventListener("resize", handleReposition);
    editorRef.current?.addEventListener("scroll", handleReposition);
    return () => {
      window.removeEventListener("resize", handleReposition);
      editorRef.current?.removeEventListener("scroll", handleReposition);
    };
  }, [selectedImage, updateOverlayForImage]);

  useEffect(() => {
    if (disabled) {
      clearImageSelection();
    }
  }, [clearImageSelection, disabled]);

  function publishEditorContent() {
    const editor = editorRef.current;
    if (!editor) {
      return;
    }
    skipSyncRef.current = true;
    onChange(readEditorHtml(editor));
  }

  function removeSelectedImage() {
    const image = selectedImageRef.current;
    if (!image) {
      return;
    }
    image.remove();
    clearImageSelection();
    publishEditorContent();
  }

  function insertImageAtCursor(imageUrl: string) {
    const editor = editorRef.current;
    if (!editor) {
      return;
    }

    const resolvedUrl = resolveBrandLogoUrl(imageUrl);
    const image = document.createElement("img");
    image.src = resolvedUrl;
    image.alt = "Signature image";
    image.className = "rich-text-editor-image";
    image.style.width = `${DEFAULT_IMAGE_WIDTH_PX}px`;
    image.style.height = "auto";

    editor.focus();

    const selection = window.getSelection();
    if (selection && selection.rangeCount > 0) {
      const range = selection.getRangeAt(0);
      if (editor.contains(range.commonAncestorContainer)) {
        range.deleteContents();
        range.insertNode(image);
        range.setStartAfter(image);
        range.collapse(true);
        selection.removeAllRanges();
        selection.addRange(range);
      } else {
        editor.appendChild(image);
      }
    } else {
      editor.appendChild(image);
    }

    const trailingBreak = document.createElement("br");
    image.insertAdjacentElement("afterend", trailingBreak);

    const finalizeInsert = () => {
      applyImageDimensions(image, DEFAULT_IMAGE_WIDTH_PX);
      selectImage(image);
      publishEditorContent();
    };

    if (image.complete) {
      finalizeInsert();
    } else {
      image.addEventListener("load", finalizeInsert, { once: true });
      image.addEventListener("error", finalizeInsert, { once: true });
    }
  }

  function runCommand(command: string, commandValue?: string) {
    if (disabled || imageUploading) {
      return;
    }
    editorRef.current?.focus();
    document.execCommand(command, false, commandValue);
    publishEditorContent();
  }

  function handleLink() {
    if (disabled || imageUploading) {
      return;
    }
    const url = window.prompt("Enter link URL (include https://)");
    if (!url?.trim()) {
      return;
    }
    runCommand("createLink", url.trim());
  }

  function handleEditorMouseDown(event: ReactMouseEvent<HTMLDivElement>) {
    if (disabled || imageUploading || resizingRef.current) {
      return;
    }

    const target = event.target;
    if (target instanceof HTMLImageElement && editorRef.current?.contains(target)) {
      event.preventDefault();
      selectImage(target);
      return;
    }

    if (!(target instanceof Element) || !target.closest(".rich-text-editor-image-resize-overlay")) {
      clearImageSelection();
    }
  }

  function handleEditorKeyDown(event: React.KeyboardEvent<HTMLDivElement>) {
    if (!selectedImageRef.current) {
      return;
    }
    if (event.key === "Delete" || event.key === "Backspace") {
      event.preventDefault();
      removeSelectedImage();
    }
  }

  function startImageResize(event: ReactMouseEvent<HTMLSpanElement>, corner: ResizeCorner) {
    event.preventDefault();
    event.stopPropagation();

    const image = selectedImageRef.current;
    const editor = editorRef.current;
    if (!image || !editor || disabled || imageUploading) {
      return;
    }

    resizingRef.current = true;
    const startX = event.clientX;
    const startY = event.clientY;
    const startWidth = image.offsetWidth;
    const startHeight = image.offsetHeight;
    const aspectRatio = startHeight / startWidth;

    function resolveNextWidth(deltaX: number, deltaY: number): number {
      if (corner === "se") {
        return startWidth + deltaX;
      }
      if (corner === "sw") {
        return startWidth - deltaX;
      }
      if (corner === "ne") {
        return startWidth + deltaX;
      }
      return startWidth - deltaX;
    }

    function onMouseMove(moveEvent: MouseEvent) {
      const deltaX = moveEvent.clientX - startX;
      const deltaY = moveEvent.clientY - startY;
      let nextWidth = resolveNextWidth(deltaX, deltaY);

      if (corner === "ne" || corner === "nw") {
        const widthFromVertical = startWidth + (corner === "ne" ? deltaY : -deltaY) * aspectRatio;
        if (Math.abs(deltaY) > Math.abs(deltaX)) {
          nextWidth = widthFromVertical;
        }
      } else if (Math.abs(deltaY) > Math.abs(deltaX)) {
        const widthFromVertical = startWidth + (corner === "se" ? deltaY : -deltaY) * aspectRatio;
        nextWidth = widthFromVertical;
      }

      applyImageDimensions(image, nextWidth);
      updateOverlayForImage(image);
    }

    function onMouseUp() {
      resizingRef.current = false;
      document.removeEventListener("mousemove", onMouseMove);
      document.removeEventListener("mouseup", onMouseUp);
      publishEditorContent();
    }

    document.addEventListener("mousemove", onMouseMove);
    document.addEventListener("mouseup", onMouseUp);
  }

  async function handleImageSelected(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    event.target.value = "";
    if (!file || disabled || imageUploading) {
      return;
    }
    if (!file.type.startsWith("image/")) {
      setImageError("Please choose an image file.");
      setImageStatus("");
      return;
    }
    if (file.size > MAX_SIGNATURE_IMAGE_BYTES) {
      setImageError("Signature images must be 5 MB or smaller.");
      setImageStatus("");
      return;
    }

    setImageError("");
    setImageStatus(`Uploading ${file.name}…`);
    setImageUploading(true);
    try {
      const imageUrl = uploadImage ? await uploadImage(file) : await readFileAsDataUrl(file);
      insertImageAtCursor(imageUrl);
      setImageStatus("Image inserted. Click it to resize with the corner handles.");
    } catch (uploadError) {
      setImageError(
        uploadError instanceof Error ? uploadError.message : "Unable to insert signature image.",
      );
      setImageStatus("");
    } finally {
      setImageUploading(false);
    }
  }

  const showPlaceholder = !value && !isFocused && !imageUploading;

  return (
    <div className={`rich-text-editor${disabled || imageUploading ? " is-disabled" : ""}`}>
      <div className="rich-text-editor-toolbar" role="toolbar" aria-label={`${ariaLabel} formatting`}>
        {FORMAT_COMMANDS.map((item) => (
          <button
            key={item.command}
            type="button"
            className="rich-text-editor-toolbar-button"
            title={item.title}
            disabled={disabled || imageUploading}
            onMouseDown={(event) => event.preventDefault()}
            onClick={() => runCommand(item.command, item.value)}
          >
            {item.label}
          </button>
        ))}
        <span className="rich-text-editor-toolbar-divider" aria-hidden="true" />
        {BLOCK_COMMANDS.map((item) => (
          <button
            key={item.command}
            type="button"
            className="rich-text-editor-toolbar-button rich-text-editor-toolbar-button--text"
            title={item.title}
            disabled={disabled || imageUploading}
            onMouseDown={(event) => event.preventDefault()}
            onClick={() => runCommand(item.command, item.value)}
          >
            {item.label}
          </button>
        ))}
        <span className="rich-text-editor-toolbar-divider" aria-hidden="true" />
        <button
          type="button"
          className="rich-text-editor-toolbar-button rich-text-editor-toolbar-button--text"
          title="Insert link"
          disabled={disabled || imageUploading}
          onMouseDown={(event) => event.preventDefault()}
          onClick={handleLink}
        >
          Link
        </button>
        <button
          type="button"
          className="rich-text-editor-toolbar-button rich-text-editor-toolbar-button--text"
          title="Insert image"
          disabled={disabled || imageUploading}
          onMouseDown={(event) => event.preventDefault()}
          onClick={() => imageInputRef.current?.click()}
        >
          {imageUploading ? "Uploading…" : "Image"}
        </button>
        <input
          ref={imageInputRef}
          type="file"
          accept="image/png,image/jpeg,image/gif,image/webp"
          className="rich-text-editor-image-input"
          onChange={(event) => void handleImageSelected(event)}
        />
      </div>

      {imageUploading ? <p className="rich-text-editor-status">Uploading image…</p> : null}
      {!imageUploading && imageStatus ? (
        <p className="rich-text-editor-status rich-text-editor-status--success">{imageStatus}</p>
      ) : null}

      <div ref={surfaceWrapRef} className="rich-text-editor-surface-wrap">
        {showPlaceholder ? <p className="rich-text-editor-placeholder">{placeholder}</p> : null}
        <div
          ref={editorRef}
          className="rich-text-editor-surface"
          style={{ minHeight }}
          contentEditable={!disabled && !imageUploading}
          role="textbox"
          aria-label={ariaLabel}
          aria-multiline="true"
          suppressContentEditableWarning
          onInput={publishEditorContent}
          onMouseDown={handleEditorMouseDown}
          onKeyDown={handleEditorKeyDown}
          onFocus={() => setIsFocused(true)}
          onBlur={() => {
            if (resizingRef.current) {
              return;
            }
            setIsFocused(false);
            clearImageSelection();
            publishEditorContent();
          }}
        />
        {selectedImage && overlayBox && !disabled && !imageUploading ? (
          <div
            className="rich-text-editor-image-resize-overlay"
            style={{
              top: overlayBox.top,
              left: overlayBox.left,
              width: overlayBox.width,
              height: overlayBox.height,
            }}
            aria-hidden="true"
          >
            {RESIZE_HANDLES.map((corner) => (
              <span
                key={corner}
                className={`rich-text-editor-image-handle rich-text-editor-image-handle--${corner}`}
                onMouseDown={(event) => startImageResize(event, corner)}
              />
            ))}
          </div>
        ) : null}
      </div>

      {imageError ? <p className="status error rich-text-editor-error">{imageError}</p> : null}
    </div>
  );
}

function readFileAsDataUrl(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => {
      if (typeof reader.result === "string") {
        resolve(reader.result);
        return;
      }
      reject(new Error("Unable to read image file."));
    };
    reader.onerror = () => reject(new Error("Unable to read image file."));
    reader.readAsDataURL(file);
  });
}
