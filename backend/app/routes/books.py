from app.models.book import Book
from app.routes.catalog_router import build_router

router, service = build_router(prefix="/books", tag="books", kind="book", model=Book, label="Book")
