"""Tests for MarkItDown integration in PDF, DOCX, and XLSX processors."""

import unittest
from unittest.mock import patch, MagicMock

import knowledge_base_builder.pdf_processor as pdf_mod
import knowledge_base_builder.document_processor as doc_mod
import knowledge_base_builder.spreadsheet_processor as sheet_mod


class TestPDFMarkItDown(unittest.TestCase):
    """Test MarkItDown integration in PDFProcessor."""

    def test_pdf_with_markitdown(self):
        """When MarkItDown is available, it should be used for PDF extraction."""
        mock_markitdown_cls = MagicMock()
        mock_result = MagicMock()
        mock_result.text_content = "PDF content via MarkItDown"
        mock_markitdown_cls.return_value.convert.return_value = mock_result

        with patch.object(pdf_mod, "_MARKITDOWN_AVAILABLE", True), \
             patch.object(pdf_mod, "MarkItDown", mock_markitdown_cls, create=True):
            text = pdf_mod.PDFProcessor.extract_text("/fake/path.pdf")

        self.assertEqual(text, "PDF content via MarkItDown")
        mock_markitdown_cls.return_value.convert.assert_called_once_with("/fake/path.pdf")

    def test_pdf_fallback(self):
        """When MarkItDown is unavailable, PyPDFLoader should be used."""
        mock_loader_cls = MagicMock()
        mock_doc = MagicMock()
        mock_doc.page_content = "PDF content via PyPDFLoader"
        mock_doc.metadata = {}
        mock_loader_cls.return_value.load.return_value = [mock_doc]

        with patch.object(pdf_mod, "_MARKITDOWN_AVAILABLE", False), \
             patch.object(pdf_mod, "PyPDFLoader", mock_loader_cls):
            text = pdf_mod.PDFProcessor.extract_text("/fake/path.pdf")

        self.assertIn("PDF content via PyPDFLoader", text)
        mock_loader_cls.assert_called_once_with("/fake/path.pdf")

    def test_pdf_markitdown_error_falls_back(self):
        """When MarkItDown raises an error, it should fall back to PyPDFLoader."""
        mock_markitdown_cls = MagicMock()
        mock_markitdown_cls.return_value.convert.side_effect = RuntimeError("conversion failed")

        mock_loader_cls = MagicMock()
        mock_doc = MagicMock()
        mock_doc.page_content = "PDF fallback content"
        mock_doc.metadata = {}
        mock_loader_cls.return_value.load.return_value = [mock_doc]

        with patch.object(pdf_mod, "_MARKITDOWN_AVAILABLE", True), \
             patch.object(pdf_mod, "MarkItDown", mock_markitdown_cls, create=True), \
             patch.object(pdf_mod, "PyPDFLoader", mock_loader_cls):
            text = pdf_mod.PDFProcessor.extract_text("/fake/path.pdf")

        self.assertIn("PDF fallback content", text)
        mock_markitdown_cls.return_value.convert.assert_called_once_with("/fake/path.pdf")
        mock_loader_cls.assert_called_once_with("/fake/path.pdf")


class TestDOCXMarkItDown(unittest.TestCase):
    """Test MarkItDown integration in DocumentProcessor for DOCX files."""

    def test_docx_with_markitdown(self):
        """When MarkItDown is available, it should be used for DOCX extraction."""
        mock_markitdown_cls = MagicMock()
        mock_result = MagicMock()
        mock_result.text_content = "DOCX content via MarkItDown"
        mock_markitdown_cls.return_value.convert.return_value = mock_result

        with patch.object(doc_mod, "_MARKITDOWN_AVAILABLE", True), \
             patch.object(doc_mod, "MarkItDown", mock_markitdown_cls, create=True):
            text = doc_mod.DocumentProcessor._extract_from_docx("/fake/path.docx")

        self.assertEqual(text, "DOCX content via MarkItDown")
        mock_markitdown_cls.return_value.convert.assert_called_once_with("/fake/path.docx")

    def test_docx_fallback(self):
        """When MarkItDown is unavailable, python-docx should be used."""
        mock_document_cls = MagicMock()
        mock_para = MagicMock()
        mock_para.text = "DOCX content via python-docx"
        mock_document_cls.return_value.paragraphs = [mock_para]

        with patch.object(doc_mod, "_MARKITDOWN_AVAILABLE", False), \
             patch.object(doc_mod, "Document", mock_document_cls):
            text = doc_mod.DocumentProcessor._extract_from_docx("/fake/path.docx")

        self.assertEqual(text, "DOCX content via python-docx")
        mock_document_cls.assert_called_once_with("/fake/path.docx")

    def test_docx_markitdown_error_falls_back(self):
        """When MarkItDown raises an error, it should fall back to python-docx."""
        mock_markitdown_cls = MagicMock()
        mock_markitdown_cls.return_value.convert.side_effect = RuntimeError("conversion failed")

        mock_document_cls = MagicMock()
        mock_para = MagicMock()
        mock_para.text = "DOCX fallback content"
        mock_document_cls.return_value.paragraphs = [mock_para]

        with patch.object(doc_mod, "_MARKITDOWN_AVAILABLE", True), \
             patch.object(doc_mod, "MarkItDown", mock_markitdown_cls, create=True), \
             patch.object(doc_mod, "Document", mock_document_cls):
            text = doc_mod.DocumentProcessor._extract_from_docx("/fake/path.docx")

        self.assertEqual(text, "DOCX fallback content")
        mock_markitdown_cls.return_value.convert.assert_called_once_with("/fake/path.docx")
        mock_document_cls.assert_called_once_with("/fake/path.docx")


class TestXLSXMarkItDown(unittest.TestCase):
    """Test MarkItDown integration in SpreadsheetProcessor for XLSX files."""

    def test_xlsx_with_markitdown(self):
        """When MarkItDown is available, it should be used for XLSX extraction."""
        mock_markitdown_cls = MagicMock()
        mock_result = MagicMock()
        mock_result.text_content = "XLSX content via MarkItDown"
        mock_markitdown_cls.return_value.convert.return_value = mock_result

        with patch.object(sheet_mod, "_MARKITDOWN_AVAILABLE", True), \
             patch.object(sheet_mod, "MarkItDown", mock_markitdown_cls, create=True):
            text = sheet_mod.SpreadsheetProcessor._extract_from_xlsx("/fake/path.xlsx")

        self.assertEqual(text, "XLSX content via MarkItDown")
        mock_markitdown_cls.return_value.convert.assert_called_once_with("/fake/path.xlsx")

    def test_xlsx_fallback(self):
        """When MarkItDown is unavailable, pandas should be used."""
        mock_pd = MagicMock()
        mock_excel = MagicMock()
        mock_excel.sheet_names = ["Sheet1"]
        mock_pd.ExcelFile.return_value = mock_excel

        mock_df = MagicMock()
        mock_df.empty = False
        mock_df.columns = ["A", "B"]
        mock_df.__len__ = lambda self: 1
        mock_df.iterrows.return_value = iter(
            [(0, MagicMock(values=["val1", "val2"]))]
        )
        mock_pd.read_excel.return_value = mock_df

        with patch.object(sheet_mod, "_MARKITDOWN_AVAILABLE", False), \
             patch.object(sheet_mod, "pd", mock_pd):
            text = sheet_mod.SpreadsheetProcessor._extract_from_xlsx("/fake/path.xlsx")

        mock_pd.ExcelFile.assert_called_once_with("/fake/path.xlsx")
        self.assertIn("Sheet1", text)

    def test_xlsx_markitdown_error_falls_back(self):
        """When MarkItDown raises an error, it should fall back to pandas."""
        mock_markitdown_cls = MagicMock()
        mock_markitdown_cls.return_value.convert.side_effect = RuntimeError("conversion failed")

        mock_pd = MagicMock()
        mock_excel = MagicMock()
        mock_excel.sheet_names = ["Sheet1"]
        mock_pd.ExcelFile.return_value = mock_excel

        mock_df = MagicMock()
        mock_df.empty = False
        mock_df.columns = ["A", "B"]
        mock_df.__len__ = lambda self: 1
        mock_df.iterrows.return_value = iter(
            [(0, MagicMock(values=["val1", "val2"]))]
        )
        mock_pd.read_excel.return_value = mock_df

        with patch.object(sheet_mod, "_MARKITDOWN_AVAILABLE", True), \
             patch.object(sheet_mod, "MarkItDown", mock_markitdown_cls, create=True), \
             patch.object(sheet_mod, "pd", mock_pd):
            text = sheet_mod.SpreadsheetProcessor._extract_from_xlsx("/fake/path.xlsx")

        mock_markitdown_cls.return_value.convert.assert_called_once_with("/fake/path.xlsx")
        mock_pd.ExcelFile.assert_called_once_with("/fake/path.xlsx")
        self.assertIn("Sheet1", text)


if __name__ == "__main__":
    unittest.main()
