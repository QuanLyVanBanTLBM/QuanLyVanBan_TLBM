import logging
from django.core.management.base import BaseCommand
from backend.services.rag_service import get_vector_collection, index_sql_document
from backend.services.sql_document_source import get_all_document_records_for_index

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Quét lại và lập chỉ mục vector cho toàn bộ văn bản SQL vào kho lưu trữ vector."

    def add_arguments(self, parser):
        parser.add_argument(
            "--source-type",
            type=str,
            choices=["vanbanden", "vanbandi", "tailieu"],
            help="Chỉ quét lại một loại văn bản cụ thể (vanbanden, vanbandi, tailieu).",
        )
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Xóa toàn bộ vector SQL cũ trước khi lập chỉ mục lại.",
        )

    def handle(self, *args, **options):
        source_type = options.get("source_type")
        clear = options.get("clear")

        if clear:
            self.stdout.write("Đang dọn dẹp vector SQL cũ...")
            try:
                collection = get_vector_collection()
                where_filter = {"source_class": "official_document"}
                if source_type:
                    where_filter["sql_doc_type"] = source_type
                collection.delete(where=where_filter)
                self.stdout.write(self.style.SUCCESS("Đã dọn dẹp vector cũ thành công."))
            except Exception as exc:
                self.stdout.write(self.style.WARNING(f"Không thể xóa vector cũ: {exc}"))

        self.stdout.write("Đang lấy danh sách văn bản cần lập chỉ mục...")
        records = get_all_document_records_for_index(source_type=source_type)
        total = len(records)
        self.stdout.write(f"Tìm thấy {total} văn bản phù hợp.")

        success_count = 0
        skipped_count = 0
        error_count = 0

        for idx, record in enumerate(records, start=1):
            doc_key = f"{record.get('source_type')}:{record.get('source_id')}"
            try:
                key = index_sql_document(record)
                if key:
                    success_count += 1
                else:
                    skipped_count += 1
            except Exception as exc:
                error_count += 1
                logger.exception("Lỗi khi lập chỉ mục %s: %s", doc_key, exc)
                self.stdout.write(self.style.ERROR(f"Lỗi khi lập chỉ mục {doc_key}: {exc}"))

            if idx % 10 == 0 or idx == total:
                self.stdout.write(f"Tiến độ: {idx}/{total}...")

        self.stdout.write(
            self.style.SUCCESS(
                f"Hoàn thành lập chỉ mục: {success_count} thành công, {skipped_count} bỏ qua, {error_count} lỗi."
            )
        )
