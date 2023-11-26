from app import app, db
from models import Category

def add_category(name):
    category = Category(name=name)
    db.session.add(category)
    db.session.commit()

def init_categories():
    categories_to_add = [
        "Еда и продукты",
        "Транспорт и автомобиль",
        "Медицина и здоровье",
        "Развлечения и культура",
        "Одежда и обувь",
        "Красота и уход",
        "Образование и курсы",
        "Коммунальные услуги",
        "Хобби и развлечения",
        "Дети и семья",
        "Дом и быт",
        "Непредвиденные траты",
        "Прочее"
    ]

    for category_name in categories_to_add:
        category = Category.query.filter_by(name=category_name).first()
        if not category:
            add_category(category_name)

if __name__ == '__main__':
    with app.app_context():
        init_categories()
        print("Categories added successfully!")
