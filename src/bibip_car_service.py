import json
import os
from models import Car, CarFullInfo, CarStatus, Model, ModelSaleStats, Sale

LINE_LENGTH = 500
FULL_LINE = LINE_LENGTH + 1


class CarService:
    def __init__(self, root_directory_path: str) -> None:
        self.root_directory_path = root_directory_path

    # метод для склеивания папки и имени файла
    def _path(self, filename: str) -> str:
        return os.path.join(self.root_directory_path, filename)

    # метод для форматирования строки
    def _make_line(self, data: str) -> str:
        return data.ljust(LINE_LENGTH) + "\n"

    # чтение индекса
    def _read_index(self, filename: str) -> list[tuple[str, int]]:
        path = self._path(filename)
        if not os.path.exists(path):
            return []
        result = []
        with open(path, "r", encoding="utf-8", newline="") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                key, line_num = line.rsplit(";", 1)
                result.append((key.strip(), int(line_num.strip())))
        return result

    # запись индекса
    def _write_index(self, filename: str, index: list[tuple[str, int]]) -> None:
        path = self._path(filename)
        with open(path, "w", encoding="utf-8", newline="") as f:
            for key, line_num in index:
                entry = f"{key};{line_num}"
                f.write(self._make_line(entry))

    # поиск по индексу
    def _find_in_index(self, index: list[tuple[str, int]], key: str) -> int | None:
        lo, hi = 0, len(index) - 1
        while lo <= hi:
            mid = (lo + hi) // 2
            if index[mid][0] == key:
                return index[mid][1]
            elif index[mid][0] < key:
                lo = mid + 1
            else:
                hi = mid - 1
        return None

    # добавление в индекс
    def _insert_into_index(
        self, index: list[tuple[str, int]], key: str, line_num: int
    ) -> list[tuple[str, int]]:
        index.append((key, line_num))
        index.sort(key=lambda x: x[0])
        return index

    # добавляем запись в конец файла
    def _append_to_file(self, filename: str, data: dict) -> int:
        path = self._path(filename)
        if os.path.exists(path):
            line_num = os.path.getsize(path) // FULL_LINE
        else:
            line_num = 0
        json_str = json.dumps(data, ensure_ascii=False, default=str)
        with open(path, "a", encoding="utf-8", newline="") as f:
            f.write(self._make_line(json_str))
        return line_num

    # читаем строку по номеру
    def _read_line(self, filename: str, line_num: int) -> dict | None:
        path = self._path(filename)
        if not os.path.exists(path):
            return None
        with open(path, "r", encoding="utf-8", newline="") as f:
            f.seek(line_num * FULL_LINE)
            raw = f.read(LINE_LENGTH)
        raw = raw.strip()
        if not raw:
            return None
        return json.loads(raw)

    # перезаписываем строку по номеру
    def _write_line(self, filename: str, line_num: int, data: dict) -> None:
        path = self._path(filename)
        json_str = json.dumps(data, ensure_ascii=False, default=str)
        with open(path, "r+", encoding="utf-8", newline="") as f:
            f.seek(line_num * FULL_LINE)
            f.write(self._make_line(json_str))

    # читаем весь файл
    def _scan_file(self, filename: str) -> list[dict]:
        path = self._path(filename)
        if not os.path.exists(path):
            return []
        result = []
        with open(path, "r", encoding="utf-8", newline="") as f:
            for line in f:
                raw = line.strip()
                if raw:
                    result.append(json.loads(raw))
        return result

    # Задание 1. Сохранение автомобилей и моделей(основной)
    def add_model(self, model: Model) -> Model:
        # Читаем текущий индекс
        index = self._read_index("models_index.txt")
        # Проверяем такая модель уже есть
        if self._find_in_index(index, str(model.id)) is not None:
            return model

        # Записываем данные модели в файл
        data = model.model_dump()
        line_num = self._append_to_file("models.txt", data)

        # Добавляем в индекс и сохраняем
        index = self._insert_into_index(index, str(model.id), line_num)
        self._write_index("models_index.txt", index)
        return model

    # Задание 1. Сохранение автомобилей и моделей(индексный)
    def add_car(self, car: Car) -> Car:
        index = self._read_index("cars_index.txt")
        if self._find_in_index(index, car.vin) is not None:
            return car
        data = car.model_dump()
        line_num = self._append_to_file("cars.txt", data)
        index = self._insert_into_index(index, car.vin, line_num)
        self._write_index("cars_index.txt", index)
        return car

    # Задание 2. Сохранение продаж.
    def sell_car(self, sale: Sale) -> Car:
        # здесь сохраняем запись о продаже
        sale_index = self._read_index("sales_index.txt")
        sale_data = sale.model_dump()
        sale_line = self._append_to_file("sales.txt", sale_data)
        sale_index = self._insert_into_index(sale_index, sale.sales_number, sale_line)
        self._write_index("sales_index.txt", sale_index)

        # здесь находим автомобиль через индекс
        cars_index = self._read_index("cars_index.txt")
        car_line = self._find_in_index(cars_index, sale.car_vin)
        if car_line is None:
            raise ValueError(f"Автомобиль с VIN {sale.car_vin} не найден")

        # здесь читаем данные машины, меняем статус, записываем обратно
        car_data = self._read_line("cars.txt", car_line)
        car_data["status"] = CarStatus.sold
        self._write_line("cars.txt", car_line, car_data)
        return Car(**car_data)

    # Задание 3. Доступные к продаже
    def get_cars(self, status: CarStatus) -> list[Car]:

        # здесь читаем все строки файла
        all_data = self._scan_file("cars.txt")
        result = []
        for data in all_data:
            # здесь пропускаем удалённые записи
            if data.get("is_deleted"):
                continue
            # здесь добавляем только машины с нужным статусом
            if data["status"] == status:
                result.append(Car(**data))
        return result

    # Задание 4. Детальная информация
    def get_car_info(self, vin: str) -> CarFullInfo | None:
        # Находим автомобиль
        cars_index = self._read_index("cars_index.txt")
        car_line = self._find_in_index(cars_index, vin)
        if car_line is None:
            return None  # если такого VIN нет
        car_data = self._read_line("cars.txt", car_line)
        # проверка удаления
        if car_data is None or car_data.get("is_deleted"):
            return None
        car = Car(**car_data)
        # Находим модель
        models_index = self._read_index("models_index.txt")
        model_line = self._find_in_index(models_index, str(car.model))
        model_data = self._read_line("models.txt", model_line)
        model = Model(**model_data)
        # Ищем продажу (если статус sold)
        sales_date = None
        sales_cost = None
        if car.status == CarStatus.sold:
            all_sales = self._scan_file("sales.txt")
            for s in all_sales:
                if s.get("is_deleted"):
                    continue
                if s["car_vin"] == vin:
                    sale = Sale(**s)
                    sales_date = sale.sales_date
                    sales_cost = sale.cost
                    break
        # собираем итоговый объект
        return CarFullInfo(
            vin=car.vin,
            car_model_name=model.name,
            car_model_brand=model.brand,
            price=car.price,
            date_start=car.date_start,
            status=car.status,
            sales_date=sales_date,
            sales_cost=sales_cost,
        )

    # Задание 5. Обновление ключевого поля
    def update_vin(self, vin: str, new_vin: str) -> Car:
        # Находим строку через индекс
        cars_index = self._read_index("cars_index.txt")
        car_line = self._find_in_index(cars_index, vin)
        if car_line is None:
            raise ValueError(f"Автомобиль с VIN {vin} не найден")
        # Читаем данные, меняем VIN, записываем обратно
        car_data = self._read_line("cars.txt", car_line)
        car_data["vin"] = new_vin
        self._write_line("cars.txt", car_line, car_data)
        # Обновляем запись в индексе
        for i, (key, ln) in enumerate(cars_index):
            if key == vin:
                cars_index[i] = (new_vin, ln)  # заменяем старый VIN на новый
                break
        # Сортируем и перезаписываем файл индекса
        cars_index.sort(key=lambda x: x[0])
        self._write_index("cars_index.txt", cars_index)
        return Car(**car_data)

    # Задание 6. Удаление продажи
    def revert_sale(self, sales_number: str) -> Car:
        # Находим запись о продаже
        sales_index = self._read_index("sales_index.txt")
        sale_line = self._find_in_index(sales_index, sales_number)
        if sale_line is None:
            raise ValueError(f"Продажа {sales_number} не найдена")
        sale_data = self._read_line("sales.txt", sale_line)
        car_vin = sale_data["car_vin"]
        # удаление: ставим флаг is_deleted = True
        sale_data["is_deleted"] = True
        self._write_line("sales.txt", sale_line, sale_data)
        # Возвращаем статус автомобиля на 'available'
        cars_index = self._read_index("cars_index.txt")
        car_line = self._find_in_index(cars_index, car_vin)
        car_data = self._read_line("cars.txt", car_line)
        car_data["status"] = CarStatus.available
        self._write_line("cars.txt", car_line, car_data)
        return Car(**car_data)

    # Задание 7. Самые продаваемые модели
    def top_models_by_sales(self) -> list[ModelSaleStats]:
        all_cars = self._scan_file("cars.txt")
        vin_to_model: dict[str, int] = {}
        for car_data in all_cars:
            if not car_data.get("is_deleted"):
                vin_to_model[car_data["vin"]] = car_data["model"]
        sales_count: dict[int, int] = {}
        sales_max_cost: dict[int, float] = {}
        all_sales = self._scan_file("sales.txt")
        for sale_data in all_sales:
            if sale_data.get("is_deleted"):
                continue
            car_vin = sale_data["car_vin"]
            model_id = vin_to_model.get(car_vin)
            if model_id is None:
                continue
            cost = float(sale_data["cost"])
            if model_id not in sales_count:
                sales_count[model_id] = 0
                sales_max_cost[model_id] = 0.0
            sales_count[model_id] += 1
            if cost > sales_max_cost[model_id]:
                sales_max_cost[model_id] = cost
        if not sales_count:
            return []
        sorted_ids = sorted(
            sales_count.keys(),
            key=lambda mid: (sales_count[mid], sales_max_cost[mid]),
            reverse=True,
        )
        result = []
        models_index = self._read_index("models_index.txt")
        for model_id in sorted_ids[:3]:
            model_line = self._find_in_index(models_index, str(model_id))
            model_data = self._read_line("models.txt", model_line)
            model = Model(**model_data)
            result.append(
                ModelSaleStats(
                    car_model_name=model.name,
                    brand=model.brand,
                    sales_number=sales_count[model_id],
                )
            )
        return result