import shutil


class FileHelper:
    def save(blob: any):
        if blob is None:
            return None

        filename = f"temp_{blob.filename}"
        print(f"FileHelper save() filename: {filename}")

        with open(filename, "wb") as buffer:
            shutil.copyfileobj(blob.file, buffer)  # Save the uploaded file temporarily.

        return filename
