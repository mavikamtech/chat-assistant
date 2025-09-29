import React, { useRef } from "react";

interface FileUploadProps {
  onFilesSelected: (files: File[]) => void;
}

export const FileUpload: React.FC<FileUploadProps> = ({ onFilesSelected }) => {
  const inputRef = useRef<HTMLInputElement | null>(null);

  const handleDrop: React.DragEventHandler<HTMLDivElement> = (e) => {
    e.preventDefault();
    const files = Array.from(e.dataTransfer.files || []);
    if (files.length) onFilesSelected(files);
  };

  const handleInput: React.ChangeEventHandler<HTMLInputElement> = (e) => {
    const files = Array.from(e.target.files || []);
    if (files.length) onFilesSelected(files);
  };

  const openPicker = () => inputRef.current?.click();

  const boxStyle: React.CSSProperties = {
    // Match attached UI exactly
    border: "2px dashed rgb(156, 163, 175)",
    borderRadius: 8,
    padding: 16,
    textAlign: "center",
    background: "rgb(255, 255, 255)",
    cursor: "pointer",
    // Make it feel like a proper drop zone
    width: "100%",
    minHeight: 120,
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    userSelect: "none",
    transition: "background-color 150ms, border-color 150ms",
  };

  return (
    <div
      style={boxStyle}
      role="button"
      tabIndex={0}
      aria-label="File upload dropzone. Click to select files or drag and drop."
      onKeyDown={(e) => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          openPicker();
        }
      }}
      onDragOver={(e) => {
        e.preventDefault();
      }}
      onDragLeave={() => {}}
      onDrop={handleDrop}
      onClick={openPicker}
    >
      <input
        ref={inputRef}
        type="file"
        style={{ display: "none" }}
        onChange={handleInput}
        multiple
      />
      <div>Drag & drop files here, or click to select</div>
    </div>
  );
};
