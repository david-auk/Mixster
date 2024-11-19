from fpdf import FPDF
from spotify import Track
from PIL import Image, ImageDraw, ImageFont
import qrcode
import math


class TrackLabel:
    def __init__(self, track, style=None):
        self.track = track
        self.track_info = {
            'name': self.track.name,
            'artist': self.track.artist,
            'date': self.track.release_date[:4]  # Just get the year
        }
        self.style = style if style is not None else {
            'font_path': 'Arial.ttf'
        }

    @staticmethod
    def __adjust_font_size(text, max_width, base_font_size, font_path):
        """Adjust the font size to make the text fit within the max_width."""
        font_size = base_font_size
        font = ImageFont.truetype(font_path, font_size)
        while font.getbbox(text)[2] > max_width and font_size > 30:  # 30 is the minimum size before wrapping
            font_size -= 2
            font = ImageFont.truetype(font_path, font_size)
        return font, font_size

    @staticmethod
    def __adjust_font_size_and_wrap(text, max_width, base_font_size, font_path):
        """First, try resizing, then apply wrapping if the font size is too small."""
        # Step 1: Resize text
        font, font_size = TrackLabel.__adjust_font_size(text, max_width, base_font_size, font_path)

        # Step 2: If font size is too small, apply wrapping
        if font_size <= 30:
            # Use wrapping if the text still doesn't fit at a reasonable font size
            wrapped_lines = TrackLabel.__wrap_text(text, font, max_width)
        else:
            # Otherwise, keep the text in a single line
            wrapped_lines = [text]

        return font, wrapped_lines

    @staticmethod
    def __wrap_text(text, font, max_width):
        """Wrap text into multiple lines to fit within the max_width."""
        words = text.split()
        lines = []
        current_line = []

        for word in words:
            current_line.append(word)
            if font.getbbox(' '.join(current_line))[2] > max_width:
                current_line.pop()  # Remove the last word that caused overflow
                lines.append(' '.join(current_line))
                current_line = [word]  # Start a new line with the overflow word

        lines.append(' '.join(current_line))  # Add the last line
        return lines

    def export(self) -> Image:
        # Higher resolution and square box with built-in margins
        img_size = 800
        margin = 80  # Margin size for cutting
        max_text_width = img_size - 2 * margin
        image = Image.new("RGB", (img_size, img_size), "white")
        draw = ImageDraw.Draw(image)

        # Load fonts
        font_path = self.style['font_path']  # Adjust to the correct path to your font file
        base_font_size = 80
        large_font = ImageFont.truetype(font_path, 160)

        # Adjust the date font
        date_text = self.track_info['date']
        date_font = large_font
        date_width = draw.textlength(date_text, font = date_font)
        date_x = (img_size - date_width) // 2
        date_y = img_size // 2 - (date_font.size / 2)  # Center the date vertically

        # Adjust the name font size and wrap text if needed
        name_text = f"\"{self.track_info['name']}\""
        name_font, name_lines = TrackLabel.__adjust_font_size_and_wrap(name_text, max_text_width, base_font_size,
                                                                       font_path)

        # Calculate the total height of the name text
        total_name_height = sum(name_font.size + 5 for _ in name_lines)
        name_y = date_y - total_name_height - 20  # Position above the date with some spacing

        # Draw the name text, line by line
        y_offset = name_y
        for line in name_lines:
            line_width = draw.textlength(line, font = name_font)
            line_x = (img_size - line_width) // 2
            draw.text((line_x, y_offset), line, fill = "black", font = name_font)
            y_offset += name_font.size + 5  # Add some spacing between lines

        # Adjust the artist font size and wrap text if needed
        artist_text = self.track_info['artist']
        artist_font_size = int(large_font.size * 0.4)  # Make artist font size smaller relative to the large font
        artist_font, artist_lines = TrackLabel.__adjust_font_size_and_wrap(artist_text, max_text_width,
                                                                           artist_font_size,
                                                                           font_path)

        # Draw the artist text, line by line, below the date
        y_offset = date_y + date_font.size + 20  # Position below the date with some spacing
        for line in artist_lines:
            artist_width = draw.textlength(line, font = artist_font)
            artist_x = (img_size - artist_width) // 2
            draw.text((artist_x, y_offset), line, fill = "black", font = artist_font)
            y_offset += artist_font.size + 5  # Add some spacing between lines

        # Draw the date text
        draw.text((date_x, date_y), date_text, fill = "black", font = date_font)

        # Save the image with built-in margins
        print(f"Track label generated")
        return image


class ColourPicker:

    def __init__(self, track_list: list[Track]):
        self.track_list = track_list

    def get_style(self, track: Track) -> dict:
        if not track in self.track_list:
            RuntimeError("Track not found in tracklist")

        style = {}

        return style


class QRCode:

    @staticmethod
    def generate(url: str) -> Image:
        # Create a QR code object with specific settings for higher resolution
        qr = qrcode.QRCode(
            version = 1,  # Controls the size of the QR code
            error_correction = qrcode.constants.ERROR_CORRECT_H,  # High error correction
            box_size = 10,  # Size of each box in the QR code grid
            border = 4  # Border thickness (minimum value is 4)
        )
        qr.add_data(url)
        qr.make(fit = True)

        # Create the QR code image
        qr_image = qr.make_image(fill = "black", back_color = "white")
        qr_image = qr_image.resize((800, 800), resample = Image.LANCZOS)  # Resize to match the track label size
        print("QR code generated")
        return qr_image


class PDF:
    labels_per_row = 3
    labels_per_column = 4
    label_width = 60  # Width of each label image
    label_height = 60  # Height of each label image
    margin_x = 15  # Margin from the left edge
    margin_y = 10  # Margin from the top edge

    @staticmethod
    def __get_tracks_per_page():
        return PDF.labels_per_row * PDF.labels_per_column

    @staticmethod
    def get_total_pages(track_amount: int) -> int:
        pages = track_amount / PDF.__get_tracks_per_page() * 2
        pages = math.ceil(pages)  # Round up
        if pages < 2:
            pages = 2  # Always at least two pages for a qr and a tracklist
        return pages

    def __init__(self, track_list: list[Track], style: dict):
        self.pdf = FPDF(orientation = 'P', unit = 'mm', format = 'A4')
        self.track_list = track_list

        # Style linting here.
        if not "font_path" in style:
            raise RuntimeError("Font path not found in style")



        self.style = style

    def export(self, output_path):
        total_tracks = len(self.track_list)
        tracks_per_page = self.labels_per_row * self.labels_per_column

        for i in range(0, total_tracks, tracks_per_page):
            # Add a page for TrackLabels
            self.pdf.add_page()

            # Arrange TrackLabels on the page
            for index in range(tracks_per_page):
                track_index = i + index
                if track_index >= total_tracks:
                    break  # No more tracks to add

                # Calculate row and column position
                row = index // PDF.labels_per_row
                col = index % PDF.labels_per_row
                x = PDF.margin_x + col * PDF.label_width
                y = PDF.margin_y + row * PDF.label_height

                # Create and place the TrackLabel image
                track = self.track_list[track_index]
                track_label = TrackLabel(track, style = self.style)
                track_label_image = track_label.export()
                self.pdf.image(track_label_image, x = x, y = y, w = PDF.label_width, h = PDF.label_height)

            # Add a page for QR codes
            self.pdf.add_page()

            # Arrange QR codes on the page in a mirrored way
            for index in range(tracks_per_page):
                track_index = i + index
                if track_index >= total_tracks:
                    break  # No more tracks to add

                # Calculate mirrored row and column position
                row = index // PDF.labels_per_row
                col = (PDF.labels_per_row - 1) - (index % PDF.labels_per_row)  # Mirror horizontally
                x = PDF.margin_x + col * PDF.label_width
                y = PDF.margin_y + row * PDF.label_height

                # Create and place the QR code image
                track = self.track_list[track_index]
                qr_code_image = QRCode.generate(track.url)
                self.pdf.image(qr_code_image, x = x, y = y, w = PDF.label_width, h = PDF.label_height)

        # Save the PDF to the specified output path
        self.pdf.output(output_path)
        print(f"PDF file exported to {output_path}")
