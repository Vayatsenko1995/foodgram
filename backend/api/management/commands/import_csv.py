"""Модуль с логикой терминальной команды для импорта CSV файла."""
import csv

from django.core.management.base import BaseCommand

from recipes.models import Ingredient, Tag

table = {
    'ingredient': Ingredient,
    'tag': Tag,
}


class Command(BaseCommand):
    help = 'Добавление данных из CSV-файла в базу данных'

    def add_arguments(self, parser):
        parser.add_argument('csv_file', type=str, help='Путь к CSV-файлу')
        parser.add_argument('object_class', type=str, help='Класс объекта')

    def handle(self, *args, **kwargs):
        csv_file = kwargs['csv_file']
        object_class = kwargs['object_class']

        with open(csv_file, 'r', encoding='UTF-8') as file:
            reader = csv.DictReader(file)
            for row in reader:
                table[object_class].objects.create(**row)

        self.stdout.write(self.style.SUCCESS('Данные добавлены успешно'))
