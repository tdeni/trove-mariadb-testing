# trove-mariadb-testing

Небольшой тестовый стед для тестирования ошибки кодировки utf-8 на разных версиях mariadb.

Для тестирования используются версии mariadb:
- 10.5
- 10.6
- 10.7

Ошибка с кодировками для mariadb 10.6+ была поправлена в этом [коммите](https://opendev.org/openstack/trove/commit/3ba1f0d955a446d96784e87411b38993e9ed7402).

В ветке `main` находится версия, в которой ошибка не исправлена. То есть запуск на этой ветке должен вызвать исключение связанное с кодировкой.

Версия с исправлениями находится в ветке `fixed`.

## Запуск
```bash
docker compose up --build -d

# запускаем проверку
docker compose exec runner python main.py
```

## Исходники
Большая часть кода взята [отсюда](https://opendev.org/openstack/trove/src/branch/master/trove/guestagent/datastore/mysql_common/service.py#L321-L346).
