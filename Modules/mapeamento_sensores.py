import os
import sys
from typing import List, Tuple

from PyQt6.QtCore import Qt, QPoint, QPointF, pyqtSignal, QObject, QRectF, QEvent
from PyQt6.QtGui import QPixmap, QColor, QPainter, QIcon
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QFrame,
    QLabel, QComboBox, QListWidget, QListWidgetItem, QGraphicsView, QGraphicsScene,
    QGraphicsPixmapItem, QGraphicsItem, QScrollArea, QGridLayout
)


DARK_THEME = {
    'bg': '#0e1116', 'top': 'rgba(20,24,30,0.85)', 'top_border': '#1f242b',
    'side_bg':'#161a21','side_border':'#232a33','side_item':'#b6c3cf','side_hover':'#212a33',
    'card_bg':'#1c222a','card_border':'#2a333d','sensor_bg':'#1a1f27','sensor_border':'#26313b',
    'text_edit_bg':'#161b22','text_edit_border':'#27313b','text':'#ffffff','muted':'#8b97a6',
    'badge_bg':'#4254b5','accent_a':'#3949ab','accent_b':'#5667c2','progress_a':'#3d4faa','progress_b':'#6073d3',
    'input_bg':'#161b22','input_border':'#28323c','checkbox_border':'#3a4652','checkbox_bg':'#182028','checkbox_border_sel':'#4f5d73','checkbox_bg_sel':'#3e51b5',
    'btn_bg':'#26313b','btn_border':'#32404c','btn_bg_hover':'#2e3a45','btn_bg_press':'#3a4753',
    'label_sensor':'#ffffff'
}


def build_qss(theme=DARK_THEME) -> str:
    btn_text_color = '#dde2e7'
    qss = (
        f"QMainWindow {{ background-color: {theme['bg']}; }}\n"
        f"QFrame#RightPanel {{ background:{theme['card_bg']}; border:1px solid {theme['card_border']}; border-radius:18px; }}\n"
        f"QLabel {{ color:{theme['text']}; }}\n"
        f"QLabel[class='section-title'] {{ font-size:14px; font-weight:600; color:{theme['text']}; }}\n"
        f"QComboBox {{ background:{theme['input_bg']}; border:1px solid {theme['input_border']}; border-radius:10px; padding:6px 10px; color:{theme['text']}; }}\n"
        f"QPushButton {{ background:{theme['btn_bg']}; border:1px solid {theme['btn_border']}; border-radius:12px; color:{btn_text_color}; padding:8px 16px; font-weight:500; }}\n"
        f"QPushButton:hover {{ background:{theme['btn_bg_hover']}; }}\n"
        f"QPushButton:pressed {{ background:{theme['btn_bg_press']}; }}\n"
        # Destaque da linha selecionada na lista de mapeamento
        f"QFrame#MapRow[selected='true'] {{ background: rgba(76, 175, 80, 0.18); border: 1px solid #4caf50; border-radius: 8px; }}\n"
        f"QFrame#MapRow {{ border: 1px solid transparent; border-radius: 8px; }}\n"
    )
    return qss


def pretty_label(raw: str) -> str:
    """Convert a filename stem like 'metacarpofalangica_indicador' into a
    nice Portuguese label like 'Metacarpofalângica Indicador'. Includes a few
    accent corrections for common terms."""
    name = os.path.splitext(os.path.basename(raw))[0].lower()
    # Direct map for known stems
    direct = {
        'mao': 'Mão',
    }
    if name in direct:
        return direct[name]
    parts = name.replace('-', '_').split('_')
    # Capitalize parts
    parts = [p.capitalize() for p in parts if p]
    label = ' '.join(parts)
    # Accent corrections
    label = label.replace('Metacarpofalangica', 'Metacarpofalângica')
    label = label.replace('Interfalangica', 'Interfalângica')
    label = label.replace('Medio', 'Médio')
    label = label.replace('Minimo', 'Mínimo')
    label = label.replace('Anelar', 'Anelar')  # keep
    label = label.replace('Indicador', 'Indicador')  # keep
    label = label.replace('Polegar', 'Polegar')  # keep
    label = label.replace('Proximal', 'Proximal')
    return label


class ArticulationSignals(QObject):
    hovered = pyqtSignal(str, QPointF)
    unhovered = pyqtSignal()
    clicked = pyqtSignal(str)


class ArticulationItem(QGraphicsPixmapItem):
    def __init__(self, name: str, pixmap: QPixmap):
        super().__init__(pixmap)
        self.signals = ArticulationSignals()
        self.setAcceptHoverEvents(True)
        # Não tornar selecionável para evitar o retângulo pontilhado padrão do Qt
        # self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, True)
        self.name = name
        self._state = 'normal'  # 'normal' | 'hover' | 'selected'
        self._pixmap = pixmap

    def _apply_state(self):
        # We recolor the pixmap by blending a tint color; images are expected to be transparent except red circle
        pm = QPixmap(self._pixmap)
        if self._state == 'normal':
            self.setPixmap(self._pixmap)
            return
        from PyQt6.QtGui import QPainter, QBrush
        color = QColor('#80d8ff') if self._state == 'hover' else QColor('#00e676')
        painter = QPainter(pm)
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceAtop)
        painter.fillRect(pm.rect(), QBrush(color))
        painter.end()
        self.setPixmap(pm)

    def hoverEnterEvent(self, event):
        if self._state != 'selected':
            self._state = 'hover'
            self._apply_state()
        self.signals.hovered.emit(self.name, event.scenePos())
        super().hoverEnterEvent(event)

    def hoverMoveEvent(self, event):
        self.signals.hovered.emit(self.name, event.scenePos())
        super().hoverMoveEvent(event)

    def hoverLeaveEvent(self, event):
        if self._state != 'selected':
            self._state = 'normal'
            self._apply_state()
        self.signals.unhovered.emit()
        super().hoverLeaveEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._state = 'selected'
            self._apply_state()
            self.signals.clicked.emit(self.name)
        super().mousePressEvent(event)

    def reset_selection(self):
        self._state = 'normal'
        self._apply_state()


class HandOverlayWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('Mapeamento de Sensores')
        self.resize(1100, 700)
        # Proíbe maximização desta janela (remove botão de maximizar)
        self.setWindowFlag(Qt.WindowType.WindowMaximizeButtonHint, False)
        # Estilo de janela não redimensionável no Windows
        self.setWindowFlag(Qt.WindowType.MSWindowsFixedSizeDialogHint, True)
        self.setStyleSheet(build_qss())
        # Ícone do app, se disponível
        try:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            icon_path = os.path.join(base_dir, 'assets', 'icon.png')
            if os.path.isfile(icon_path):
                self.setWindowIcon(QIcon(icon_path))
        except Exception:
            pass

        # Estado de mapeamento
        self.mapping = {}
        self.combo_by_name = {}

        # Root layout
        root = QWidget()
        main = QHBoxLayout(root)
        # Remover margens para maximizar a área útil do viewport
        main.setContentsMargins(0, 0, 0, 0)
        main.setSpacing(16)

        # Left: Graphics view (stacked images)
        self.view = QGraphicsView()
        self.view.setRenderHints(
            self.view.renderHints()
            | QPainter.RenderHint.Antialiasing
            | QPainter.RenderHint.SmoothPixmapTransform
        )
        # Ajustes para comportamento de visualização
        self.view.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.view.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.view.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorViewCenter)
        self.view.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorViewCenter)
        # Remover moldura do QGraphicsView para aproveitar cada pixel
        self.view.setFrameShape(QFrame.Shape.NoFrame)
        self.scene = QGraphicsScene(self)
        self.view.setScene(self.scene)
        main.addWidget(self.view, 1)

        # Right: Selection panel
        right = QFrame(); right.setObjectName('RightPanel')
        right.setMinimumWidth(420)
        rp = QVBoxLayout(right); rp.setContentsMargins(16,16,16,16); rp.setSpacing(12)
        title = QLabel('Mapeamento de Articulações → Sensores')
        title.setProperty('class','section-title')
        rp.addWidget(title)

        # Área rolável com grid
        self.scroll = QScrollArea(); self.scroll.setWidgetResizable(True)
        self.map_container = QWidget(); self.map_layout = QGridLayout(self.map_container)
        self.map_layout.setContentsMargins(0,0,0,0)
        self.map_layout.setHorizontalSpacing(10)
        self.map_layout.setVerticalSpacing(8)
        self.scroll.setWidget(self.map_container)
        rp.addWidget(self.scroll, 1)

        # Removido indicador textual; usaremos realce direto na lista
        rp.addStretch(1)
        # Legend label near mouse (overlay)
        self.mouse_label = QLabel('', self.view)
        self.mouse_label.setStyleSheet('QLabel { background: rgba(0,0,0,140); color: #ffffff; padding: 4px 8px; border-radius: 8px; }')
        self.mouse_label.setVisible(False)

        main.addWidget(right, 0)
        self.setCentralWidget(root)

        # Load images
        base_path = self._find_mao_folder()
        self._load_images(base_path)
        # Carrega config existente e monta painel
        self._load_config_mapping()
        self._build_mapping_panel()
        # Proíbe redimensionamento por arrastar as bordas: fixa o tamanho atual
        self.setFixedSize(self.size())

    def showEvent(self, event):
        super().showEvent(event)
        # Reajusta ao exibir e conecta sinal de troca de tela (DPI/escala)
        self._fit_view()
        try:
            wh = self.windowHandle()
            if wh and not getattr(self, '_screen_signal_connected', False):
                wh.screenChanged.connect(self._on_screen_changed)
                self._screen_signal_connected = True
        except Exception:
            pass

    def _on_screen_changed(self, _screen):
        # Quando mover para outro monitor, refaz ajuste
        self._fit_view()

    def changeEvent(self, event):
        # Impede que a janela seja maximizada por atalhos do SO
        if event.type() == QEvent.Type.WindowStateChange and self.isMaximized():
            self.showNormal()
        super().changeEvent(event)

    def _fit_view(self):
        # Ajusta a imagem para que a ALTURA ocupe exatamente a altura da janela
        if self.scene is None:
            return
        try:
            rect = self._base_item.sceneBoundingRect() if getattr(self, '_base_item', None) is not None else self.scene.itemsBoundingRect()
        except Exception:
            return
        if rect.width() <= 0 or rect.height() <= 0:
            return
        vp = self.view.viewport().size()
        if vp.height() <= 0:
            return
        # Escala baseada apenas na altura para que a imagem caiba exatamente
        sy = vp.height() / rect.height()
        self.view.resetTransform()
        self.view.scale(sy, sy)
        # Center the view on the base rect center
        self.view.centerOn(rect.center())

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._fit_view()

    def _find_mao_folder(self) -> str:
        # Try several common variants
        candidates = [
            os.path.join('assets','mao'),
            os.path.join('assets','Mao'),
            os.path.join('Assets','mao'),
            os.path.join('assets','MAO'),
            os.path.join('Assets','MAO'),
        ]
        for c in candidates:
            if os.path.isdir(c):
                return c
        # Fallback: allow running from repo root regardless of CWD
        here = os.path.dirname(os.path.abspath(__file__))
        repo_root = os.path.abspath(os.path.join(here, '..'))
        for c in candidates:
            p = os.path.join(repo_root, c)
            if os.path.isdir(p):
                return p
        # As a last resort, use assets root so app opens; will show message
        return os.path.join('assets')

    def _split_base_and_overlays(self, files: List[str]) -> Tuple[str, List[str]]:
        base = ''
        overlays: List[str] = []
        for f in files:
            name = os.path.basename(f).lower()
            if 'mao' in name and (name.endswith('.png') or name.endswith('.webp') or name.endswith('.jpg') or name.endswith('.jpeg')):
                # prefer this as base silhouette
                base = f
            else:
                overlays.append(f)
        if not base and overlays:
            # pick the first as base if not explicitly found
            base = overlays[0]; overlays = overlays[1:]
        return base, overlays

    def _load_images(self, mao_folder: str):
        if not os.path.isdir(mao_folder):
            info = QLabel(f"Pasta não encontrada: {mao_folder}")
            info.setStyleSheet('color:#ff8a80;')
            self.scene.clear(); self.scene.addWidget(info)
            return
        files = [os.path.join(mao_folder, f) for f in os.listdir(mao_folder)
                 if f.lower().endswith(('.png','.webp','.jpg','.jpeg'))]
        if not files:
            info = QLabel(f"Nenhuma imagem encontrada em: {mao_folder}")
            info.setStyleSheet('color:#ff8a80;')
            self.scene.clear(); self.scene.addWidget(info)
            return
        base, overlays = self._split_base_and_overlays(files)
        self.scene.clear()
        # Base silhouette
        base_pm = QPixmap(base)
        if base_pm.isNull():
            base_item = self.scene.addText('Falha ao carregar imagem base')
        else:
            base_item = QGraphicsPixmapItem(base_pm)
            base_item.setZValue(0)
            self.scene.addItem(base_item)
            # Usa boundingRect do item para dimensões lógicas corretas
            br = base_item.boundingRect()
            self.view.setSceneRect(QRectF(0, 0, br.width(), br.height()))
        # guarda referência para ajuste de zoom
        self._base_item = base_item if isinstance(base_item, QGraphicsPixmapItem) else None
        # Markers
        self.items: List[ArticulationItem] = []
        for path in overlays:
            pm = QPixmap(path)
            if pm.isNull():
                continue
            name = os.path.splitext(os.path.basename(path))[0]
            item = ArticulationItem(name=name, pixmap=pm)
            item.setZValue(1)
            # same origin/position; images presumed same size
            item.setPos(0, 0)
            item.signals.hovered.connect(self._on_item_hovered)
            item.signals.unhovered.connect(self._on_item_unhovered)
            item.signals.clicked.connect(self._on_item_clicked)
            self.scene.addItem(item)
            self.items.append(item)
        # Lista de articulações para painel
        self.articulation_names = [it.name for it in self.items]
        # Ajusta a visualização após carregar
        self._fit_view()

    def _on_item_hovered(self, name: str, pos: QPointF):
        # show label near cursor inside the view, incluindo sensor atribuído
        sensor = (self.mapping.get(name) if hasattr(self, 'mapping') else None) or 'Nenhum'
        self.mouse_label.setText(f"{pretty_label(name)} — Sensor: {sensor}")
        self.mouse_label.adjustSize()
        # map scene pos to view coordinates
        vp = self.view.mapFromScene(pos)
        self.mouse_label.move(vp.x() + 14, vp.y() + 14)
        self.mouse_label.setVisible(True)

    def _on_item_unhovered(self):
        self.mouse_label.setVisible(False)

    def _on_item_clicked(self, name: str):
        # Apenas destaca seleção
        for it in self.items:
            if it.name != name:
                it.reset_selection()
        # Realça a linha correspondente na lista
        self._highlight_row(name)

    # ---------- Config (carregar/salvar) ----------
    def _config_path(self) -> str:
        return os.path.join(os.getcwd(), 'config.json')

    def _load_config_mapping(self):
        try:
            import json
            with open(self._config_path(), 'r', encoding='utf-8') as f:
                cfg = json.load(f)
            self.mapping = dict(cfg.get('sensorMapping', {}))
        except Exception:
            self.mapping = {}

    def _save_config_mapping(self):
        try:
            import json
            cfg = {}
            try:
                with open(self._config_path(), 'r', encoding='utf-8') as f:
                    cfg = json.load(f)
            except Exception:
                cfg = {}
            cfg['sensorMapping'] = self.mapping
            with open(self._config_path(), 'w', encoding='utf-8') as f:
                json.dump(cfg, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    # ---------- Painel de mapeamento ----------
    def _build_mapping_panel(self):
        # Limpa grid
        if hasattr(self, 'map_layout'):
            while self.map_layout.count():
                it = self.map_layout.takeAt(0)
                w = it.widget()
                if w:
                    w.deleteLater()
        self.combo_by_name = {}
        self.row_by_name = {}
        names = sorted(getattr(self, 'articulation_names', []))
        all_sensors = [f'flex{i}' for i in range(1,9)]
        for row, name in enumerate(names):
            row_frame = QFrame(); row_frame.setObjectName('MapRow')
            hl = QHBoxLayout(row_frame); hl.setContentsMargins(8,6,8,6); hl.setSpacing(8)
            lbl = QLabel(pretty_label(name))
            cmb = QComboBox(); cmb.setEditable(False)
            cmb.currentTextChanged.connect(lambda _v, n=name: self._on_combo_changed(n))
            self.combo_by_name[name] = cmb
            self.row_by_name[name] = row_frame
            hl.addWidget(lbl, 1)
            hl.addWidget(cmb, 1)
            self.map_layout.addWidget(row_frame, row, 0, 1, 2)
        # Preenche opções respeitando unicidade
        self._refresh_combo_options()

    def _highlight_row(self, name: str):
        try:
            for n, row in self.row_by_name.items():
                row.setProperty('selected', 'true' if n == name else 'false')
                row.style().unpolish(row); row.style().polish(row); row.update()
            # Garantir visibilidade
            if name in self.row_by_name:
                self.scroll.ensureWidgetVisible(self.row_by_name[name])
        except Exception:
            pass

    def _used_sensors(self) -> set:
        return {v for v in self.mapping.values() if v and v != 'Nenhum'}

    def _refresh_combo_options(self):
        all_sensors = [f'flex{i}' for i in range(1,9)]
        for name, cmb in self.combo_by_name.items():
            current = self.mapping.get(name, 'Nenhum')
            used = self._used_sensors() - ({current} if current else set())
            available = ['Nenhum'] + [s for s in all_sensors if s not in used]
            prev = cmb.currentText()
            cmb.blockSignals(True)
            cmb.clear(); cmb.addItems(available)
            target = current if current in available else (prev if prev in available else 'Nenhum')
            cmb.setCurrentText(target)
            cmb.blockSignals(False)

    def _on_combo_changed(self, name: str):
        cmb = self.combo_by_name.get(name)
        if not cmb:
            return
        sel = cmb.currentText()
        self.mapping[name] = sel if sel != 'Nenhum' else 'Nenhum'
        self._refresh_combo_options()
        self._save_config_mapping()


def main():
    app = QApplication(sys.argv)
    win = HandOverlayWindow()
    win.show()
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
