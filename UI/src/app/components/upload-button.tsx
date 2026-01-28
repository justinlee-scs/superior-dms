export function UploadButton({
  onUpload,
}: {
  onUpload: (file: File) => void;
}) {
  return (
    <input
      type="file"
      onChange={(e) => {
        const file = e.target.files?.[0];
        if (file) onUpload(file);
      }}
    />
  );
}
