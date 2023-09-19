class Query(object):
    def __init__(self, columns=None, tables=None, where=None, order=None,
                 group=None, limit=None):
        self.columns = columns or []
        self.tables = tables or []
        self.where = where or []
        self.order = order or []
        self.group = group or []
        self.limit = limit

    def __repr__(self):
        return str(self)

    @property
    def _columns(self):
        if not self.columns:
            return "SELECT *"
        return "SELECT %s" % (", ".join(self.columns))

    @property
    def _tables(self):
        return "FROM %s" % (", ".join(self.tables))

    @property
    def _where(self):
        if not self.where:
            return ""
        return "WHERE %s" % (" AND ".join(self.where))

    @property
    def _order(self):
        if not self.order:
            return ""
        return "ORDER BY %s" % (", ".join(self.order))

    @property
    def _group_by(self):
        if not self.group:
            return ""
        return "GROUP BY %s" % (", ".join(self.group))

    @property
    def _limit(self):
        if not self.limit:
            return ""
        return "LIMIT %s" % str(self.limit)

    def __str__(self):
        query = [
            self._columns,
            self._tables,
            self._where,
            self._order,
            self._group_by,
            self._limit,
        ]
        query = [q for q in query if q]
        return " ".join(query) + ";"
