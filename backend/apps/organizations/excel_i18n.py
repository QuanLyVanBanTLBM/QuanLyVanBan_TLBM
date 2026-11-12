EXCEL_TRANSLATIONS = {
    "vi": {
        "organizations.export.sheetTitle": "Danh bạ",
        "organizations.export.filenamePrefix": "DanhBa_BAOLONG",
        "organizations.export.title": "Bảo Long Insurance — Hệ Thống Quản Lý Văn Bản & Điều Hành",
        "organizations.export.subtitle": "Danh bạ đơn vị, phòng ban",
        "organizations.export.generatedLabel": "Ngày xuất",
        "organizations.export.headers": [
            "STT",
            "Họ và tên",
            "Chức vụ",
            "Chức danh",
            "Điện thoại",
            "Email",
        ],
        "organizations.export.addressLabel": "Địa chỉ",
        "organizations.export.phoneLabel": "ĐT",
        "organizations.export.emailLabel": "Email",
    },
    "en": {
        "organizations.export.sheetTitle": "Directory",
        "organizations.export.filenamePrefix": "Directory_BAOLONG",
        "organizations.export.title": "Bảo Long Insurance — Document Management & Operations System",
        "organizations.export.subtitle": "Departments directory",
        "organizations.export.generatedLabel": "Exported at",
        "organizations.export.headers": [
            "No.",
            "Full name",
            "Position",
            "Job title",
            "Phone",
            "Email",
        ],
        "organizations.export.addressLabel": "Address",
        "organizations.export.phoneLabel": "Tel",
        "organizations.export.emailLabel": "Email",
    },
}


def get_excel_translations(lang):
    selected = EXCEL_TRANSLATIONS.get(lang, EXCEL_TRANSLATIONS["vi"])
    return {
        "sheet_title": selected["organizations.export.sheetTitle"],
        "filename_prefix": selected["organizations.export.filenamePrefix"],
        "title": selected["organizations.export.title"],
        "subtitle": selected["organizations.export.subtitle"],
        "generated_label": selected["organizations.export.generatedLabel"],
        "headers": selected["organizations.export.headers"],
        "address_label": selected["organizations.export.addressLabel"],
        "phone_label": selected["organizations.export.phoneLabel"],
        "email_label": selected["organizations.export.emailLabel"],
    }
