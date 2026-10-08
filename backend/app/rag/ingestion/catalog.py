"""Edition-specific profiles. A different PDF must be reviewed before parsing."""
from dataclasses import dataclass


@dataclass(frozen=True)
class Book:
    id: str
    filename: str
    title: str
    author: str
    sha256: str
    ocr_pending: bool = False


BOOKS: dict[str, Book] = {}
BOOKS['nabulsi'] = Book('nabulsi', 'nabulsi.pdf', 'تعطير الأنام في تعبير المنام', 'عبد الغني النابلسي', 'f19ae1359524a3223646b59fdf021239f4d1c792f7392983d8b722db13c68e05', False)
BOOKS['ibn-Shahin'] = Book('ibn-Shahin', 'ibn-Shahin.pdf', 'الإشارات في علم العبارات', 'ابن شاهين الظاهري', 'cf1a9175ffc9aadb5c266a489528cb132c5fa013493fa8be83447d6e1bbb0989', False)
BOOKS['ibn-sirin'] = Book('ibn-sirin', 'ibn-sirine.pdf', 'منتخب الكلام في تفسير الأحلام', 'منسوب إلى ابن سيرين؛ النسبة غير مؤكدة', '5cc7fa99744499424466b1fdec159809c823e9e180de266685ffafef2668e481', True)
