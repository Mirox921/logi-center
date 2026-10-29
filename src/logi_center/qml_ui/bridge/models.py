from pathlib import Path

from PySide6.QtCore import QAbstractListModel, QModelIndex, Qt, QByteArray, Property, Signal


class DeviceListModel(QAbstractListModel):
    countChanged = Signal()
    """Stable-ID list model; changing battery data never resets the page/model."""
    DeviceIdRole = Qt.ItemDataRole.UserRole + 1
    ObjectRole = DeviceIdRole + 1
    _roles = {DeviceIdRole: QByteArray(b'deviceId'), ObjectRole: QByteArray(b'device')}

    def __init__(self, parent=None):
        super().__init__(parent)
        self._rows = []
        self._by_id = {}

    @Property(int, notify=countChanged)
    def count(self):
        return len(self._rows)

    def roleNames(self):
        return self._roles

    def rowCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() else len(self._rows)

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid() or index.row() < 0 or index.row() >= len(self._rows):
            return None
        row = self._rows[index.row()]
        if role == self.DeviceIdRole:
            return row['deviceId']
        if role == self.ObjectRole:
            return row
        if role == Qt.ItemDataRole.DisplayRole:
            return row.get('name', '')
        return None

    def get(self, row):
        return self._rows[row] if 0 <= row < len(self._rows) else {}

    def byId(self, device_id):
        row = self._by_id.get(str(device_id), -1)
        return self.get(row)

    def update(self, rows):
        incoming = {str(r['deviceId']): dict(r) for r in rows}
        wanted = [str(r['deviceId']) for r in rows]
        # Remove only absent IDs. Existing rows remain stable during state changes.
        for i in range(len(self._rows) - 1, -1, -1):
            if self._rows[i]['deviceId'] not in incoming:
                self.beginRemoveRows(QModelIndex(), i, i)
                del self._rows[i]
                self.endRemoveRows()
                self.countChanged.emit()
        self._reindex()
        # Update existing stable IDs in place and append newly discovered IDs.
        for device_id in wanted:
            if device_id in self._by_id:
                row_index = self._by_id[device_id]
                old = self._rows[row_index]
                new = incoming[device_id]
                if old != new:
                    self._rows[row_index] = new
                    self.dataChanged.emit(self.index(row_index, 0), self.index(row_index, 0), [self.ObjectRole])
                continue
            row_index = len(self._rows)
            self.beginInsertRows(QModelIndex(), row_index, row_index)
            self._rows.append(incoming[device_id])
            self.endInsertRows()
            self.countChanged.emit()
            self._reindex()
        self._reindex()

    def _reindex(self):
        self._by_id = {r['deviceId']: i for i, r in enumerate(self._rows)}


class CapabilityListModel(QAbstractListModel):
    countChanged = Signal()
    CapabilityRole = Qt.ItemDataRole.UserRole + 1
    _roles = {CapabilityRole: QByteArray(b'capability')}

    def __init__(self, parent=None):
        super().__init__(parent)
        self._rows = []
        self._by_id = {}

    @Property(int, notify=countChanged)
    def count(self):
        return len(self._rows)

    def roleNames(self):
        return self._roles

    def rowCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() else len(self._rows)

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid() or not 0 <= index.row() < len(self._rows):
            return None
        value = self._rows[index.row()]
        return value if role in (self.CapabilityRole, Qt.ItemDataRole.DisplayRole) else None

    def update(self, capabilities):
        rows = {str(row['id']): dict(row) for row in capabilities}
        wanted = list(rows)
        for i in range(len(self._rows) - 1, -1, -1):
            if self._rows[i]['id'] not in rows:
                self.beginRemoveRows(QModelIndex(), i, i)
                del self._rows[i]
                self.endRemoveRows()
                self.countChanged.emit()
        self._reindex()
        for ident in wanted:
            if ident in self._by_id:
                i = self._by_id[ident]
                if self._rows[i] != rows[ident]:
                    self._rows[i] = rows[ident]
                    self.dataChanged.emit(self.index(i, 0), self.index(i, 0), [self.CapabilityRole])
            else:
                i = len(self._rows)
                self.beginInsertRows(QModelIndex(), i, i)
                self._rows.append(rows[ident])
                self.endInsertRows()
                self.countChanged.emit()
                self._reindex()
        self._reindex()

    def _reindex(self):
        self._by_id = {row['id']: i for i, row in enumerate(self._rows)}
