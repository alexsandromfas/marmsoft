"""
Módulo de Gestão Clínica para MarmSoft.

Este módulo implementa:
- Persistência de pacientes e terapeutas em CSV
- Overlay inicial com navegação por abas (Novo Paciente, Abrir Paciente, Cadastrar Terapeuta)
- Gerenciamento de sessões clínicas
- Validações e feedback visual

Arquivos gerados:
- therapists.csv: Lista central de terapeutas
- Pacientes/<id>.csv: Um arquivo por paciente
- sessions.csv: Metadados das sessões clínicas
"""

from __future__ import annotations

import csv
import os
import uuid
import logging
import tempfile
import shutil
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Dict, Callable, Any

from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QObject
from PyQt6.QtGui import QFont, QColor
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, QGridLayout,
    QLabel, QPushButton, QLineEdit, QComboBox, QSpinBox, QDateEdit,
    QTextEdit, QFrame, QStackedWidget, QListWidget, QListWidgetItem,
    QMessageBox, QGraphicsDropShadowEffect, QScrollArea, QTableWidget,
    QTableWidgetItem, QHeaderView, QAbstractItemView, QDialog
)

# Configuração de logging interno (não exposto ao usuário)
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
_handler = logging.StreamHandler()
_handler.setFormatter(logging.Formatter('[%(asctime)s] %(levelname)s - %(message)s'))
logger.addHandler(_handler)


# ===================== Dataclasses =====================

@dataclass
class Therapist:
    """Modelo de dados do terapeuta."""
    registro: str
    nome: str
    telefone: str = ""
    email: str = ""
    clinica: str = ""
    observacoes: str = ""


@dataclass
class PatientData:
    """Modelo de dados do paciente."""
    id: str
    nome: str
    data_nascimento: str = ""
    idade: int = 0
    sexo: str = ""
    condicao: str = ""
    grau_comprometimento: str = ""
    mao_comprometida: str = ""
    mao_dominante: str = ""
    data_diagnostico: str = ""
    terapeuta: str = ""
    registro_terapeuta: str = ""
    contato: str = ""
    observacoes: str = ""


@dataclass
class SessionData:
    """Modelo de dados da sessão clínica."""
    session_id: str
    patient_id: str
    therapist_registro: str
    therapist_nome: str
    start_time: str
    end_time: str = ""
    duracao: str = ""
    notas: str = ""


# ===================== Constantes =====================

PATIENTS_DIR = "Pacientes"
THERAPISTS_DIR = "Terapeutas"
THERAPISTS_FILE = os.path.join(THERAPISTS_DIR, "therapists.csv")
SESSIONS_FILE = "sessions.csv"

PATIENT_HEADER = [
    "id", "nome", "data_nascimento", "idade", "sexo", "condicao",
    "grau_comprometimento", "mao_comprometida", "mao_dominante",
    "data_diagnostico", "terapeuta", "registro_terapeuta", "contato", "observacoes"
]

THERAPIST_HEADER = ["registro", "nome", "telefone", "email", "clinica", "observacoes"]

SESSION_HEADER = [
    "session_id", "patient_id", "therapist_registro", "therapist_nome",
    "start_time", "end_time", "duracao", "notas"
]


# ===================== Funções de Persistência =====================

def _ensure_dir(path: str) -> None:
    """Cria diretório se não existir."""
    if not os.path.exists(path):
        os.makedirs(path)


def _atomic_write_csv(filepath: str, header: List[str], rows: List[List[str]]) -> None:
    """Escreve CSV de forma atômica (temporário + rename) para evitar corrupção."""
    _ensure_dir(os.path.dirname(filepath) or ".")
    temp_fd, temp_path = tempfile.mkstemp(suffix=".csv", dir=os.path.dirname(filepath) or ".")
    try:
        with os.fdopen(temp_fd, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(header)
            writer.writerows(rows)
        # Move atomicamente
        shutil.move(temp_path, filepath)
    except Exception as e:
        # Limpa temp se falhar
        if os.path.exists(temp_path):
            os.remove(temp_path)
        logger.error(f"Falha ao escrever {filepath}: {e}")
        raise


def _read_csv_rows(filepath: str) -> List[Dict[str, str]]:
    """Lê CSV e retorna lista de dicionários."""
    if not os.path.exists(filepath):
        return []
    try:
        with open(filepath, 'r', newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            return list(reader)
    except Exception as e:
        logger.error(f"Falha ao ler {filepath}: {e}")
        return []


# --------- Terapeutas ---------

def load_therapists() -> List[Therapist]:
    """Carrega todos os terapeutas do arquivo CSV."""
    rows = _read_csv_rows(THERAPISTS_FILE)
    therapists = []
    for row in rows:
        try:
            therapists.append(Therapist(
                registro=row.get("registro", ""),
                nome=row.get("nome", ""),
                telefone=row.get("telefone", ""),
                email=row.get("email", ""),
                clinica=row.get("clinica", ""),
                observacoes=row.get("observacoes", "")
            ))
        except Exception as e:
            logger.warning(f"Linha de terapeuta inválida: {e}")
    return therapists


def save_therapist(therapist: Therapist) -> bool:
    """
    Salva ou atualiza terapeuta. Retorna False se duplicata de registro (novo).
    Se já existir com mesmo registro, atualiza os dados.
    """
    existing = load_therapists()
    
    # Verifica se é atualização ou novo
    updated = False
    for i, t in enumerate(existing):
        if t.registro == therapist.registro:
            existing[i] = therapist
            updated = True
            break
    
    if not updated:
        existing.append(therapist)
    
    rows = [
        [t.registro, t.nome, t.telefone, t.email, t.clinica, t.observacoes]
        for t in existing
    ]
    
    try:
        _ensure_dir(THERAPISTS_DIR)
        _atomic_write_csv(THERAPISTS_FILE, THERAPIST_HEADER, rows)
        return True
    except Exception:
        return False


def therapist_exists(registro: str) -> bool:
    """Verifica se terapeuta com dado registro já existe."""
    for t in load_therapists():
        if t.registro == registro:
            return True
    return False


# --------- Pacientes ---------

def list_patients() -> List[PatientData]:
    """Lista todos os pacientes da pasta Pacientes/."""
    _ensure_dir(PATIENTS_DIR)
    patients = []
    try:
        for fname in os.listdir(PATIENTS_DIR):
            # Ignora arquivos auxiliares: _sessions.csv, _flybird.csv, _mapping.json, etc.
            if not fname.endswith('.csv'):
                continue
            if fname.endswith('_sessions.csv') or fname.endswith('_flybird.csv'):
                continue
            patient_id = fname[:-4]  # Remove .csv
            patient = load_patient(patient_id)
            if patient:
                patients.append(patient)
    except Exception as e:
        logger.error(f"Falha ao listar pacientes: {e}")
    return patients


def load_patient(patient_id: str) -> Optional[PatientData]:
    """Carrega dados de um paciente específico."""
    filepath = os.path.join(PATIENTS_DIR, f"{patient_id}.csv")
    rows = _read_csv_rows(filepath)
    if not rows:
        return None
    
    row = rows[0]  # Primeira linha após header contém os dados
    try:
        return PatientData(
            id=row.get("id", patient_id),
            nome=row.get("nome", ""),
            data_nascimento=row.get("data_nascimento", ""),
            idade=int(row.get("idade", 0) or 0),
            sexo=row.get("sexo", ""),
            condicao=row.get("condicao", ""),
            grau_comprometimento=row.get("grau_comprometimento", ""),
            mao_comprometida=row.get("mao_comprometida", ""),
            mao_dominante=row.get("mao_dominante", ""),
            data_diagnostico=row.get("data_diagnostico", ""),
            terapeuta=row.get("terapeuta", ""),
            registro_terapeuta=row.get("registro_terapeuta", ""),
            contato=row.get("contato", ""),
            observacoes=row.get("observacoes", "")
        )
    except Exception as e:
        logger.error(f"Falha ao carregar paciente {patient_id}: {e}")
        return None


def save_patient(patient: PatientData) -> bool:
    """Salva dados do paciente em CSV individual."""
    _ensure_dir(PATIENTS_DIR)
    filepath = os.path.join(PATIENTS_DIR, f"{patient.id}.csv")
    
    row = [
        patient.id, patient.nome, patient.data_nascimento, str(patient.idade),
        patient.sexo, patient.condicao, patient.grau_comprometimento,
        patient.mao_comprometida, patient.mao_dominante, patient.data_diagnostico,
        patient.terapeuta, patient.registro_terapeuta, patient.contato, patient.observacoes
    ]
    
    try:
        _atomic_write_csv(filepath, PATIENT_HEADER, [row])
        return True
    except Exception:
        return False


def patient_exists(patient_id: str) -> bool:
    """Verifica se paciente com dado ID já existe."""
    filepath = os.path.join(PATIENTS_DIR, f"{patient_id}.csv")
    return os.path.exists(filepath)


def generate_next_patient_id() -> str:
    """
    Gera automaticamente o próximo ID de paciente no formato P001, P002, etc.
    Analisa os IDs existentes e retorna o próximo disponível.
    """
    _ensure_dir(PATIENTS_DIR)
    max_num = 0
    
    try:
        for fname in os.listdir(PATIENTS_DIR):
            if fname.endswith('.csv') and not fname.endswith('_sessions.csv'):
                patient_id = fname[:-4]  # Remove .csv
                # Tenta extrair número do formato PXXX
                if patient_id.startswith('P') and len(patient_id) >= 2:
                    try:
                        num = int(patient_id[1:])
                        max_num = max(max_num, num)
                    except ValueError:
                        continue
    except Exception as e:
        logger.warning(f"Erro ao listar pacientes para gerar ID: {e}")
    
    next_num = max_num + 1
    return f"P{next_num:03d}"


def delete_patient(patient_id: str) -> bool:
    """Remove arquivo do paciente (com confirmação prévia no UI)."""
    filepath = os.path.join(PATIENTS_DIR, f"{patient_id}.csv")
    try:
        if os.path.exists(filepath):
            os.remove(filepath)
        return True
    except Exception as e:
        logger.error(f"Falha ao remover paciente {patient_id}: {e}")
        return False


# --------- Sessões ---------

def open_session(patient_id: str, therapist_registro: str, therapist_nome: str) -> SessionData:
    """Cria nova sessão e registra no arquivo de sessões."""
    session = SessionData(
        session_id=str(uuid.uuid4()),
        patient_id=patient_id,
        therapist_registro=therapist_registro,
        therapist_nome=therapist_nome,
        start_time=datetime.now().isoformat()
    )
    
    # Salva no arquivo central
    _save_session_row(session)
    
    return session


def close_session(session: SessionData, notas: str = "") -> SessionData:
    """Encerra sessão, calcula duração e salva."""
    session.end_time = datetime.now().isoformat()
    session.notas = notas
    
    # Calcula duração
    try:
        start = datetime.fromisoformat(session.start_time)
        end = datetime.fromisoformat(session.end_time)
        delta = end - start
        hours, remainder = divmod(int(delta.total_seconds()), 3600)
        minutes, seconds = divmod(remainder, 60)
        session.duracao = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
    except Exception:
        session.duracao = "00:00:00"
    
    # Atualiza no arquivo central
    _update_session_row(session)
    
    # Mantém apenas as últimas 20 sessões no histórico
    trim_sessions_history(20)
    
    return session


def _save_session_row(session: SessionData) -> None:
    """Adiciona nova sessão ao arquivo CSV."""
    filepath = SESSIONS_FILE
    existing = _read_csv_rows(filepath)
    
    rows = []
    for row in existing:
        rows.append([
            row.get("session_id", ""),
            row.get("patient_id", ""),
            row.get("therapist_registro", ""),
            row.get("therapist_nome", ""),
            row.get("start_time", ""),
            row.get("end_time", ""),
            row.get("duracao", ""),
            row.get("notas", "")
        ])
    
    rows.append([
        session.session_id, session.patient_id, session.therapist_registro,
        session.therapist_nome, session.start_time, session.end_time,
        session.duracao, session.notas
    ])
    
    _atomic_write_csv(filepath, SESSION_HEADER, rows)


def _update_session_row(session: SessionData) -> None:
    """Atualiza sessão existente no arquivo CSV."""
    filepath = SESSIONS_FILE
    existing = _read_csv_rows(filepath)
    
    rows = []
    for row in existing:
        if row.get("session_id") == session.session_id:
            rows.append([
                session.session_id, session.patient_id, session.therapist_registro,
                session.therapist_nome, session.start_time, session.end_time,
                session.duracao, session.notas
            ])
        else:
            rows.append([
                row.get("session_id", ""),
                row.get("patient_id", ""),
                row.get("therapist_registro", ""),
                row.get("therapist_nome", ""),
                row.get("start_time", ""),
                row.get("end_time", ""),
                row.get("duracao", ""),
                row.get("notas", "")
            ])
    
    _atomic_write_csv(filepath, SESSION_HEADER, rows)


def get_patient_sessions(patient_id: str) -> List[SessionData]:
    """Retorna todas as sessões de um paciente."""
    rows = _read_csv_rows(SESSIONS_FILE)
    sessions = []
    for row in rows:
        if row.get("patient_id") == patient_id:
            sessions.append(SessionData(
                session_id=row.get("session_id", ""),
                patient_id=row.get("patient_id", ""),
                therapist_registro=row.get("therapist_registro", ""),
                therapist_nome=row.get("therapist_nome", ""),
                start_time=row.get("start_time", ""),
                end_time=row.get("end_time", ""),
                duracao=row.get("duracao", ""),
                notas=row.get("notas", "")
            ))
    return sessions


def has_active_session(patient_id: str) -> bool:
    """Verifica se há sessão ativa (sem end_time) para o paciente."""
    rows = _read_csv_rows(SESSIONS_FILE)
    for row in rows:
        if row.get("patient_id") == patient_id and not row.get("end_time"):
            return True
    return False


def load_recent_sessions(limit: int = 20) -> List[SessionData]:
    """
    Carrega as últimas N sessões do histórico.
    
    Parameters
    ----------
    limit : int
        Número máximo de sessões a retornar (padrão: 20)
    
    Returns
    -------
    List[SessionData]
        Lista das últimas sessões, ordenadas da mais recente para mais antiga.
    """
    rows = _read_csv_rows(SESSIONS_FILE)
    sessions = []
    for row in rows:
        sessions.append(SessionData(
            session_id=row.get("session_id", ""),
            patient_id=row.get("patient_id", ""),
            therapist_registro=row.get("therapist_registro", ""),
            therapist_nome=row.get("therapist_nome", ""),
            start_time=row.get("start_time", ""),
            end_time=row.get("end_time", ""),
            duracao=row.get("duracao", ""),
            notas=row.get("notas", "")
        ))
    
    # Ordena por start_time decrescente e retorna os últimos N
    sessions.sort(key=lambda s: s.start_time, reverse=True)
    return sessions[:limit]


def trim_sessions_history(max_sessions: int = 20) -> None:
    """
    Mantém apenas as últimas N sessões no arquivo CSV.
    Deleta sessões antigas além do limite.
    """
    rows = _read_csv_rows(SESSIONS_FILE)
    if len(rows) <= max_sessions:
        return
    
    # Ordena por start_time e mantém as mais recentes
    rows.sort(key=lambda r: r.get("start_time", ""), reverse=True)
    rows = rows[:max_sessions]
    
    # Reescreve o arquivo
    csv_rows = []
    for row in rows:
        csv_rows.append([
            row.get("session_id", ""),
            row.get("patient_id", ""),
            row.get("therapist_registro", ""),
            row.get("therapist_nome", ""),
            row.get("start_time", ""),
            row.get("end_time", ""),
            row.get("duracao", ""),
            row.get("notas", "")
        ])
    
    _atomic_write_csv(SESSIONS_FILE, SESSION_HEADER, csv_rows)


# ===================== Widgets de Feedback =====================

class FeedbackLabel(QLabel):
    """Label com estilos de sucesso/aviso/erro."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWordWrap(True)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.hide()
    
    def show_success(self, message: str):
        self.setText(message)
        self.setStyleSheet("""
            background-color: #1b5e20;
            color: #a5d6a7;
            padding: 8px 12px;
            border-radius: 4px;
            font-weight: bold;
        """)
        self.show()
        QTimer.singleShot(3000, self.hide)
    
    def show_warning(self, message: str):
        self.setText(message)
        self.setStyleSheet("""
            background-color: #f57f17;
            color: #fff8e1;
            padding: 8px 12px;
            border-radius: 4px;
            font-weight: bold;
        """)
        self.show()
        QTimer.singleShot(4000, self.hide)
    
    def show_error(self, message: str):
        self.setText(message)
        self.setStyleSheet("""
            background-color: #b71c1c;
            color: #ffcdd2;
            padding: 8px 12px;
            border-radius: 4px;
            font-weight: bold;
        """)
        self.show()
        QTimer.singleShot(4000, self.hide)


# ===================== Formulários =====================

class NewPatientForm(QWidget):
    """Formulário para cadastro de novo paciente."""
    
    saved = pyqtSignal()
    cancelled = pyqtSignal()
    
    def __init__(self, therapists_provider: Callable[[], List[Therapist]], parent=None):
        super().__init__(parent)
        self._get_therapists = therapists_provider
        self._setup_ui()
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        
        # Título
        title = QLabel("Novo Paciente")
        title.setProperty("class", "section-title")
        title.setStyleSheet("font-size: 18px; font-weight: bold; margin-bottom: 10px;")
        layout.addWidget(title)
        
        # Scroll area para o formulário
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        
        form_widget = QWidget()
        form = QFormLayout(form_widget)
        form.setSpacing(10)
        form.setContentsMargins(0, 0, 10, 0)
        
        # Campos
        self.ed_id = QLineEdit()
        self.ed_id.setReadOnly(True)
        self.ed_id.setStyleSheet("background-color: #3a3a3a; color: #aaa;")
        self.ed_id.setText(generate_next_patient_id())
        self.ed_id.setToolTip("ID gerado automaticamente")
        
        self.ed_nome = QLineEdit()
        self.ed_nome.setPlaceholderText("Nome completo (obrigatório)")
        
        self.ed_nascimento = QDateEdit()
        self.ed_nascimento.setCalendarPopup(True)
        self.ed_nascimento.setDisplayFormat("dd/MM/yyyy")
        
        self.sp_idade = QSpinBox()
        self.sp_idade.setRange(0, 150)
        self.sp_idade.setValue(30)
        
        self.cb_sexo = QComboBox()
        self.cb_sexo.addItems(["", "Masculino", "Feminino", "Outro"])
        
        self.ed_condicao = QLineEdit()
        self.ed_condicao.setPlaceholderText("Ex: AVC, Parkinson, Pós-operatório...")
        
        self.cb_grau = QComboBox()
        self.cb_grau.addItems(["", "Leve", "Moderado", "Grave"])
        
        self.cb_mao_comprometida = QComboBox()
        self.cb_mao_comprometida.addItems(["", "Direita", "Esquerda", "Bilateral"])
        
        self.cb_mao_dominante = QComboBox()
        self.cb_mao_dominante.addItems(["", "Direita", "Esquerda"])
        
        self.ed_data_diag = QDateEdit()
        self.ed_data_diag.setCalendarPopup(True)
        self.ed_data_diag.setDisplayFormat("dd/MM/yyyy")
        
        self.cb_terapeuta = QComboBox()
        self._refresh_therapists()
        
        self.ed_contato = QLineEdit()
        self.ed_contato.setPlaceholderText("Telefone ou email")
        
        self.ed_obs = QTextEdit()
        self.ed_obs.setPlaceholderText("Observações clínicas...")
        self.ed_obs.setMaximumHeight(80)
        
        # Adiciona campos ao form
        form.addRow("ID *", self.ed_id)
        form.addRow("Nome *", self.ed_nome)
        form.addRow("Data Nascimento", self.ed_nascimento)
        form.addRow("Idade", self.sp_idade)
        form.addRow("Sexo", self.cb_sexo)
        form.addRow("Condição", self.ed_condicao)
        form.addRow("Grau Comprometimento", self.cb_grau)
        form.addRow("Mão Comprometida", self.cb_mao_comprometida)
        form.addRow("Mão Dominante", self.cb_mao_dominante)
        form.addRow("Data Diagnóstico", self.ed_data_diag)
        form.addRow("Terapeuta", self.cb_terapeuta)
        form.addRow("Contato", self.ed_contato)
        form.addRow("Observações", self.ed_obs)
        
        scroll.setWidget(form_widget)
        layout.addWidget(scroll, 1)
        
        # Feedback
        self.feedback = FeedbackLabel()
        layout.addWidget(self.feedback)
        
        # Botões
        btn_row = QHBoxLayout()
        btn_row.setSpacing(12)
        
        self.btn_save = QPushButton("Salvar")
        self.btn_save.setProperty("class", "action")
        self.btn_save.clicked.connect(self._on_save)
        
        self.btn_cancel = QPushButton("Cancelar")
        self.btn_cancel.clicked.connect(self._on_cancel)
        
        btn_row.addStretch()
        btn_row.addWidget(self.btn_cancel)
        btn_row.addWidget(self.btn_save)
        
        layout.addLayout(btn_row)
    
    def _refresh_therapists(self):
        """Atualiza combo de terapeutas."""
        self.cb_terapeuta.clear()
        self.cb_terapeuta.addItem("", "")
        for t in self._get_therapists():
            self.cb_terapeuta.addItem(f"{t.nome} ({t.registro})", t.registro)
    
    def _on_save(self):
        # Validação
        patient_id = self.ed_id.text().strip()
        nome = self.ed_nome.text().strip()
        
        if not nome:
            self.feedback.show_error("Nome do paciente é obrigatório!")
            return
        
        # Segurança: verifica duplicata mesmo com ID auto-gerado
        if patient_exists(patient_id):
            # Regenera ID se por algum motivo já existir
            patient_id = generate_next_patient_id()
            self.ed_id.setText(patient_id)
        
        # Coleta dados
        terapeuta_reg = self.cb_terapeuta.currentData() or ""
        terapeuta_nome = ""
        if terapeuta_reg:
            for t in self._get_therapists():
                if t.registro == terapeuta_reg:
                    terapeuta_nome = t.nome
                    break
        
        patient = PatientData(
            id=patient_id,
            nome=nome,
            data_nascimento=self.ed_nascimento.date().toString("dd/MM/yyyy"),
            idade=self.sp_idade.value(),
            sexo=self.cb_sexo.currentText(),
            condicao=self.ed_condicao.text().strip(),
            grau_comprometimento=self.cb_grau.currentText(),
            mao_comprometida=self.cb_mao_comprometida.currentText(),
            mao_dominante=self.cb_mao_dominante.currentText(),
            data_diagnostico=self.ed_data_diag.date().toString("dd/MM/yyyy"),
            terapeuta=terapeuta_nome,
            registro_terapeuta=terapeuta_reg,
            contato=self.ed_contato.text().strip(),
            observacoes=self.ed_obs.toPlainText().strip()
        )
        
        if save_patient(patient):
            self.feedback.show_success(f"Paciente '{nome}' cadastrado com sucesso!")
            QTimer.singleShot(1500, self.saved.emit)
        else:
            self.feedback.show_error("Erro ao salvar paciente. Verifique os logs.")
    
    def _on_cancel(self):
        self.cancelled.emit()
    
    def reset(self):
        """Limpa o formulário."""
        self.ed_id.clear()
        self.ed_nome.clear()
        self.sp_idade.setValue(30)
        self.cb_sexo.setCurrentIndex(0)
        self.ed_condicao.clear()
        self.cb_grau.setCurrentIndex(0)
        self.cb_mao_comprometida.setCurrentIndex(0)
        self.cb_mao_dominante.setCurrentIndex(0)
        self.cb_terapeuta.setCurrentIndex(0)
        self.ed_contato.clear()
        self.ed_obs.clear()
        self._refresh_therapists()


class OpenPatientForm(QWidget):
    """Formulário para abrir/editar paciente existente."""
    
    patient_selected = pyqtSignal(str)  # Emite patient_id
    session_started = pyqtSignal(str, str, str)  # patient_id, therapist_registro, therapist_nome
    closed = pyqtSignal()
    
    def __init__(self, therapists_provider: Callable[[], List[Therapist]], parent=None):
        super().__init__(parent)
        self._get_therapists = therapists_provider
        self._current_patient: Optional[PatientData] = None
        self._setup_ui()
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        
        # Título
        title = QLabel("Abrir Paciente")
        title.setProperty("class", "section-title")
        title.setStyleSheet("font-size: 18px; font-weight: bold; margin-bottom: 10px;")
        layout.addWidget(title)
        
        # Busca
        search_row = QHBoxLayout()
        self.ed_search = QLineEdit()
        self.ed_search.setPlaceholderText("Buscar por nome ou ID...")
        self.ed_search.textChanged.connect(self._filter_list)
        search_row.addWidget(self.ed_search)
        layout.addLayout(search_row)
        
        # Lista de pacientes
        self.list_patients = QListWidget()
        self.list_patients.itemClicked.connect(self._on_patient_clicked)
        self.list_patients.setMaximumHeight(150)
        layout.addWidget(self.list_patients)
        
        # Área de detalhes/edição
        self.detail_frame = QFrame()
        self.detail_frame.setObjectName("SensorCard")
        detail_layout = QVBoxLayout(self.detail_frame)
        detail_layout.setContentsMargins(12, 12, 12, 12)
        
        self.lbl_detail_title = QLabel("Selecione um paciente")
        self.lbl_detail_title.setStyleSheet("font-size: 14px; font-weight: bold;")
        detail_layout.addWidget(self.lbl_detail_title)
        
        # Formulário de edição (scrollable)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        
        edit_widget = QWidget()
        self.edit_form = QFormLayout(edit_widget)
        self.edit_form.setSpacing(8)
        
        self.ed_edit_nome = QLineEdit()
        self.ed_edit_condicao = QLineEdit()
        self.cb_edit_grau = QComboBox()
        self.cb_edit_grau.addItems(["", "Leve", "Moderado", "Grave"])
        self.ed_edit_contato = QLineEdit()
        self.ed_edit_obs = QTextEdit()
        self.ed_edit_obs.setMaximumHeight(60)
        self.cb_edit_terapeuta = QComboBox()
        
        self.edit_form.addRow("Nome", self.ed_edit_nome)
        self.edit_form.addRow("Condição", self.ed_edit_condicao)
        self.edit_form.addRow("Grau", self.cb_edit_grau)
        self.edit_form.addRow("Contato", self.ed_edit_contato)
        self.edit_form.addRow("Terapeuta", self.cb_edit_terapeuta)
        self.edit_form.addRow("Observações", self.ed_edit_obs)
        
        scroll.setWidget(edit_widget)
        detail_layout.addWidget(scroll, 1)
        
        layout.addWidget(self.detail_frame, 1)
        
        # Feedback
        self.feedback = FeedbackLabel()
        layout.addWidget(self.feedback)
        
        # Botões de ação
        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)
        
        self.btn_save = QPushButton("Salvar Alterações")
        self.btn_save.setProperty("class", "action")
        self.btn_save.clicked.connect(self._on_save)
        self.btn_save.setEnabled(False)
        
        self.btn_new_session = QPushButton("Nova Sessão")
        self.btn_new_session.clicked.connect(self._on_new_session)
        self.btn_new_session.setEnabled(False)
        
        self.btn_delete = QPushButton("Remover")
        self.btn_delete.setStyleSheet("background-color: #b71c1c;")
        self.btn_delete.clicked.connect(self._on_delete)
        self.btn_delete.setEnabled(False)
        
        self.btn_close = QPushButton("Voltar")
        self.btn_close.clicked.connect(self.closed.emit)
        
        btn_row.addWidget(self.btn_delete)
        btn_row.addStretch()
        btn_row.addWidget(self.btn_close)
        btn_row.addWidget(self.btn_new_session)
        btn_row.addWidget(self.btn_save)
        
        layout.addLayout(btn_row)
    
    def refresh(self):
        """Atualiza lista de pacientes e terapeutas."""
        self._refresh_therapists()
        self._refresh_patients()
        self._current_patient = None
        self.btn_save.setEnabled(False)
        self.btn_new_session.setEnabled(False)
        self.btn_delete.setEnabled(False)
        self.lbl_detail_title.setText("Selecione um paciente")
        self.ed_edit_nome.clear()
        self.ed_edit_condicao.clear()
        self.cb_edit_grau.setCurrentIndex(0)
        self.ed_edit_contato.clear()
        self.ed_edit_obs.clear()
    
    def _refresh_therapists(self):
        self.cb_edit_terapeuta.clear()
        self.cb_edit_terapeuta.addItem("", "")
        for t in self._get_therapists():
            self.cb_edit_terapeuta.addItem(f"{t.nome} ({t.registro})", t.registro)
    
    def _refresh_patients(self):
        self.list_patients.clear()
        for p in list_patients():
            item = QListWidgetItem(f"{p.id} - {p.nome}")
            item.setData(Qt.ItemDataRole.UserRole, p.id)
            self.list_patients.addItem(item)
    
    def _filter_list(self, text: str):
        text_lower = text.lower()
        for i in range(self.list_patients.count()):
            item = self.list_patients.item(i)
            visible = text_lower in item.text().lower() if text else True
            item.setHidden(not visible)
    
    def _on_patient_clicked(self, item: QListWidgetItem):
        patient_id = item.data(Qt.ItemDataRole.UserRole)
        patient = load_patient(patient_id)
        if not patient:
            self.feedback.show_error("Erro ao carregar paciente")
            return
        
        self._current_patient = patient
        self.lbl_detail_title.setText(f"Paciente: {patient.nome} ({patient.id})")
        
        # Preenche campos
        self.ed_edit_nome.setText(patient.nome)
        self.ed_edit_condicao.setText(patient.condicao)
        
        idx = self.cb_edit_grau.findText(patient.grau_comprometimento)
        self.cb_edit_grau.setCurrentIndex(idx if idx >= 0 else 0)
        
        self.ed_edit_contato.setText(patient.contato)
        self.ed_edit_obs.setPlainText(patient.observacoes)
        
        # Terapeuta
        idx_t = self.cb_edit_terapeuta.findData(patient.registro_terapeuta)
        self.cb_edit_terapeuta.setCurrentIndex(idx_t if idx_t >= 0 else 0)
        
        self.btn_save.setEnabled(True)
        self.btn_new_session.setEnabled(True)
        self.btn_delete.setEnabled(True)
        
        self.patient_selected.emit(patient_id)
    
    def _on_save(self):
        if not self._current_patient:
            return
        
        # Atualiza dados
        self._current_patient.nome = self.ed_edit_nome.text().strip()
        self._current_patient.condicao = self.ed_edit_condicao.text().strip()
        self._current_patient.grau_comprometimento = self.cb_edit_grau.currentText()
        self._current_patient.contato = self.ed_edit_contato.text().strip()
        self._current_patient.observacoes = self.ed_edit_obs.toPlainText().strip()
        
        terapeuta_reg = self.cb_edit_terapeuta.currentData() or ""
        self._current_patient.registro_terapeuta = terapeuta_reg
        for t in self._get_therapists():
            if t.registro == terapeuta_reg:
                self._current_patient.terapeuta = t.nome
                break
        
        if save_patient(self._current_patient):
            self.feedback.show_success("Alterações salvas!")
            self._refresh_patients()
        else:
            self.feedback.show_error("Erro ao salvar alterações")
    
    def _on_new_session(self):
        if not self._current_patient:
            return
        
        # Verificar sessão ativa
        if has_active_session(self._current_patient.id):
            self.feedback.show_warning("Este paciente já possui uma sessão ativa!")
            return
        
        terapeuta_reg = self.cb_edit_terapeuta.currentData() or ""
        terapeuta_nome = ""
        for t in self._get_therapists():
            if t.registro == terapeuta_reg:
                terapeuta_nome = t.nome
                break
        
        self.session_started.emit(
            self._current_patient.id,
            terapeuta_reg,
            terapeuta_nome
        )
    
    def _on_delete(self):
        if not self._current_patient:
            return
        
        reply = QMessageBox.question(
            self,
            "Confirmar Exclusão",
            f"Deseja realmente remover o paciente '{self._current_patient.nome}'?\n\n"
            "Esta ação não pode ser desfeita.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            if delete_patient(self._current_patient.id):
                self.feedback.show_success("Paciente removido!")
                QTimer.singleShot(1000, self.refresh)
            else:
                self.feedback.show_error("Erro ao remover paciente")


class TherapistForm(QWidget):
    """Formulário para cadastro de terapeuta."""
    
    saved = pyqtSignal()
    cancelled = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        
        # Título
        title = QLabel("Cadastrar Terapeuta")
        title.setProperty("class", "section-title")
        title.setStyleSheet("font-size: 18px; font-weight: bold; margin-bottom: 10px;")
        layout.addWidget(title)
        
        # Formulário
        form = QFormLayout()
        form.setSpacing(10)
        
        self.ed_registro = QLineEdit()
        self.ed_registro.setPlaceholderText("Ex: CREFITO 12345 (obrigatório)")
        
        self.ed_nome = QLineEdit()
        self.ed_nome.setPlaceholderText("Nome completo (obrigatório)")
        
        self.ed_telefone = QLineEdit()
        self.ed_telefone.setPlaceholderText("(11) 99999-9999")
        
        self.ed_email = QLineEdit()
        self.ed_email.setPlaceholderText("email@exemplo.com")
        
        self.ed_clinica = QLineEdit()
        self.ed_clinica.setPlaceholderText("Nome da clínica (opcional)")
        
        self.ed_obs = QTextEdit()
        self.ed_obs.setPlaceholderText("Observações...")
        self.ed_obs.setMaximumHeight(80)
        
        form.addRow("Registro *", self.ed_registro)
        form.addRow("Nome *", self.ed_nome)
        form.addRow("Telefone", self.ed_telefone)
        form.addRow("Email", self.ed_email)
        form.addRow("Clínica", self.ed_clinica)
        form.addRow("Observações", self.ed_obs)
        
        layout.addLayout(form)
        layout.addStretch()
        
        # Feedback
        self.feedback = FeedbackLabel()
        layout.addWidget(self.feedback)
        
        # Botões
        btn_row = QHBoxLayout()
        btn_row.setSpacing(12)
        
        self.btn_save = QPushButton("Salvar")
        self.btn_save.setProperty("class", "action")
        self.btn_save.clicked.connect(self._on_save)
        
        self.btn_cancel = QPushButton("Cancelar")
        self.btn_cancel.clicked.connect(self._on_cancel)
        
        btn_row.addStretch()
        btn_row.addWidget(self.btn_cancel)
        btn_row.addWidget(self.btn_save)
        
        layout.addLayout(btn_row)
    
    def _on_save(self):
        registro = self.ed_registro.text().strip()
        nome = self.ed_nome.text().strip()
        
        if not registro:
            self.feedback.show_error("Registro profissional é obrigatório!")
            return
        
        if not nome:
            self.feedback.show_error("Nome é obrigatório!")
            return
        
        # Verifica duplicata somente se for novo
        if therapist_exists(registro):
            reply = QMessageBox.question(
                self,
                "Terapeuta Existente",
                f"Terapeuta com registro '{registro}' já existe.\n\n"
                "Deseja atualizar os dados?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply != QMessageBox.StandardButton.Yes:
                return
        
        therapist = Therapist(
            registro=registro,
            nome=nome,
            telefone=self.ed_telefone.text().strip(),
            email=self.ed_email.text().strip(),
            clinica=self.ed_clinica.text().strip(),
            observacoes=self.ed_obs.toPlainText().strip()
        )
        
        if save_therapist(therapist):
            self.feedback.show_success(f"Terapeuta '{nome}' cadastrado com sucesso!")
            QTimer.singleShot(1500, self.saved.emit)
        else:
            self.feedback.show_error("Erro ao salvar terapeuta")
    
    def _on_cancel(self):
        self.cancelled.emit()
    
    def reset(self):
        """Limpa o formulário."""
        self.ed_registro.clear()
        self.ed_nome.clear()
        self.ed_telefone.clear()
        self.ed_email.clear()
        self.ed_clinica.clear()
        self.ed_obs.clear()


# ===================== Dialogs de Edição =====================

class EditPatientDialog(QDialog):
    """Dialog para editar dados de um paciente existente."""
    
    patient_updated = pyqtSignal()
    
    def __init__(self, patient: PatientData, therapists_provider: Callable[[], List[Therapist]], parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Editar Paciente: {patient.nome}")
        self.setMinimumSize(500, 600)
        self._patient = patient
        self._get_therapists = therapists_provider
        self._setup_ui()
        self._load_patient_data()
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        
        # Scroll área para o formulário
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        
        form_widget = QWidget()
        form = QFormLayout(form_widget)
        form.setSpacing(10)
        
        # ID (readonly)
        self.ed_id = QLineEdit()
        self.ed_id.setReadOnly(True)
        self.ed_id.setStyleSheet("background-color: #3a3a3a; color: #aaa;")
        
        self.ed_nome = QLineEdit()
        self.ed_nascimento = QDateEdit()
        self.ed_nascimento.setCalendarPopup(True)
        self.ed_nascimento.setDisplayFormat("dd/MM/yyyy")
        
        self.sp_idade = QSpinBox()
        self.sp_idade.setRange(0, 150)
        
        self.cb_sexo = QComboBox()
        self.cb_sexo.addItems(["", "Masculino", "Feminino", "Outro"])
        
        self.ed_condicao = QLineEdit()
        
        self.cb_grau = QComboBox()
        self.cb_grau.addItems(["", "Leve", "Moderado", "Grave"])
        
        self.cb_mao_comprometida = QComboBox()
        self.cb_mao_comprometida.addItems(["", "Direita", "Esquerda", "Bilateral"])
        
        self.cb_mao_dominante = QComboBox()
        self.cb_mao_dominante.addItems(["", "Direita", "Esquerda"])
        
        self.ed_data_diag = QDateEdit()
        self.ed_data_diag.setCalendarPopup(True)
        self.ed_data_diag.setDisplayFormat("dd/MM/yyyy")
        
        self.cb_terapeuta = QComboBox()
        self._refresh_therapists()
        
        self.ed_contato = QLineEdit()
        
        self.ed_obs = QTextEdit()
        self.ed_obs.setMaximumHeight(80)
        
        form.addRow("ID", self.ed_id)
        form.addRow("Nome *", self.ed_nome)
        form.addRow("Data Nascimento", self.ed_nascimento)
        form.addRow("Idade", self.sp_idade)
        form.addRow("Sexo", self.cb_sexo)
        form.addRow("Condição", self.ed_condicao)
        form.addRow("Grau Comprometimento", self.cb_grau)
        form.addRow("Mão Comprometida", self.cb_mao_comprometida)
        form.addRow("Mão Dominante", self.cb_mao_dominante)
        form.addRow("Data Diagnóstico", self.ed_data_diag)
        form.addRow("Terapeuta", self.cb_terapeuta)
        form.addRow("Contato", self.ed_contato)
        form.addRow("Observações", self.ed_obs)
        
        scroll.setWidget(form_widget)
        layout.addWidget(scroll, 1)
        
        # Botões
        btn_row = QHBoxLayout()
        btn_row.setSpacing(12)
        
        self.btn_save = QPushButton("Salvar")
        self.btn_save.setProperty("class", "action")
        self.btn_save.clicked.connect(self._on_save)
        
        self.btn_cancel = QPushButton("Cancelar")
        self.btn_cancel.clicked.connect(self.reject)
        
        btn_row.addStretch()
        btn_row.addWidget(self.btn_cancel)
        btn_row.addWidget(self.btn_save)
        
        layout.addLayout(btn_row)
    
    def _refresh_therapists(self):
        self.cb_terapeuta.clear()
        self.cb_terapeuta.addItem("", "")
        for t in self._get_therapists():
            self.cb_terapeuta.addItem(f"{t.nome} ({t.registro})", t.registro)
    
    def _load_patient_data(self):
        """Preenche os campos com os dados do paciente."""
        p = self._patient
        self.ed_id.setText(p.id)
        self.ed_nome.setText(p.nome)
        
        if p.data_nascimento:
            from PyQt6.QtCore import QDate
            date = QDate.fromString(p.data_nascimento, "dd/MM/yyyy")
            if date.isValid():
                self.ed_nascimento.setDate(date)
        
        self.sp_idade.setValue(p.idade)
        
        idx = self.cb_sexo.findText(p.sexo)
        self.cb_sexo.setCurrentIndex(idx if idx >= 0 else 0)
        
        self.ed_condicao.setText(p.condicao)
        
        idx = self.cb_grau.findText(p.grau_comprometimento)
        self.cb_grau.setCurrentIndex(idx if idx >= 0 else 0)
        
        idx = self.cb_mao_comprometida.findText(p.mao_comprometida)
        self.cb_mao_comprometida.setCurrentIndex(idx if idx >= 0 else 0)
        
        idx = self.cb_mao_dominante.findText(p.mao_dominante)
        self.cb_mao_dominante.setCurrentIndex(idx if idx >= 0 else 0)
        
        if p.data_diagnostico:
            from PyQt6.QtCore import QDate
            date = QDate.fromString(p.data_diagnostico, "dd/MM/yyyy")
            if date.isValid():
                self.ed_data_diag.setDate(date)
        
        idx = self.cb_terapeuta.findData(p.registro_terapeuta)
        self.cb_terapeuta.setCurrentIndex(idx if idx >= 0 else 0)
        
        self.ed_contato.setText(p.contato)
        self.ed_obs.setPlainText(p.observacoes)
    
    def _on_save(self):
        nome = self.ed_nome.text().strip()
        if not nome:
            QMessageBox.warning(self, "Validação", "Nome é obrigatório!")
            return
        
        # Coleta terapeuta
        terapeuta_reg = self.cb_terapeuta.currentData() or ""
        terapeuta_nome = ""
        if terapeuta_reg:
            for t in self._get_therapists():
                if t.registro == terapeuta_reg:
                    terapeuta_nome = t.nome
                    break
        
        # Atualiza patient
        self._patient.nome = nome
        self._patient.data_nascimento = self.ed_nascimento.date().toString("dd/MM/yyyy")
        self._patient.idade = self.sp_idade.value()
        self._patient.sexo = self.cb_sexo.currentText()
        self._patient.condicao = self.ed_condicao.text().strip()
        self._patient.grau_comprometimento = self.cb_grau.currentText()
        self._patient.mao_comprometida = self.cb_mao_comprometida.currentText()
        self._patient.mao_dominante = self.cb_mao_dominante.currentText()
        self._patient.data_diagnostico = self.ed_data_diag.date().toString("dd/MM/yyyy")
        self._patient.terapeuta = terapeuta_nome
        self._patient.registro_terapeuta = terapeuta_reg
        self._patient.contato = self.ed_contato.text().strip()
        self._patient.observacoes = self.ed_obs.toPlainText().strip()
        
        if save_patient(self._patient):
            self.patient_updated.emit()
            self.accept()
        else:
            QMessageBox.critical(self, "Erro", "Erro ao salvar paciente!")


class EditTherapistDialog(QDialog):
    """Dialog para editar dados de um terapeuta existente."""
    
    therapist_updated = pyqtSignal()
    
    def __init__(self, therapist: Therapist, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Editar Terapeuta: {therapist.nome}")
        self.setMinimumSize(450, 400)
        self._therapist = therapist
        self._setup_ui()
        self._load_therapist_data()
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        
        form = QFormLayout()
        form.setSpacing(10)
        
        # Registro (readonly - é a chave)
        self.ed_registro = QLineEdit()
        self.ed_registro.setReadOnly(True)
        self.ed_registro.setStyleSheet("background-color: #3a3a3a; color: #aaa;")
        
        self.ed_nome = QLineEdit()
        self.ed_telefone = QLineEdit()
        self.ed_email = QLineEdit()
        self.ed_clinica = QLineEdit()
        
        self.ed_obs = QTextEdit()
        self.ed_obs.setMaximumHeight(80)
        
        form.addRow("Registro", self.ed_registro)
        form.addRow("Nome *", self.ed_nome)
        form.addRow("Telefone", self.ed_telefone)
        form.addRow("Email", self.ed_email)
        form.addRow("Clínica", self.ed_clinica)
        form.addRow("Observações", self.ed_obs)
        
        layout.addLayout(form)
        layout.addStretch()
        
        # Botões
        btn_row = QHBoxLayout()
        btn_row.setSpacing(12)
        
        self.btn_save = QPushButton("Salvar")
        self.btn_save.setProperty("class", "action")
        self.btn_save.clicked.connect(self._on_save)
        
        self.btn_cancel = QPushButton("Cancelar")
        self.btn_cancel.clicked.connect(self.reject)
        
        btn_row.addStretch()
        btn_row.addWidget(self.btn_cancel)
        btn_row.addWidget(self.btn_save)
        
        layout.addLayout(btn_row)
    
    def _load_therapist_data(self):
        """Preenche os campos com os dados do terapeuta."""
        t = self._therapist
        self.ed_registro.setText(t.registro)
        self.ed_nome.setText(t.nome)
        self.ed_telefone.setText(t.telefone)
        self.ed_email.setText(t.email)
        self.ed_clinica.setText(t.clinica)
        self.ed_obs.setPlainText(t.observacoes)
    
    def _on_save(self):
        nome = self.ed_nome.text().strip()
        if not nome:
            QMessageBox.warning(self, "Validação", "Nome é obrigatório!")
            return
        
        # Atualiza dados
        self._therapist.nome = nome
        self._therapist.telefone = self.ed_telefone.text().strip()
        self._therapist.email = self.ed_email.text().strip()
        self._therapist.clinica = self.ed_clinica.text().strip()
        self._therapist.observacoes = self.ed_obs.toPlainText().strip()
        
        if save_therapist(self._therapist):
            self.therapist_updated.emit()
            self.accept()
        else:
            QMessageBox.critical(self, "Erro", "Erro ao salvar terapeuta!")


# ===================== Overlay Principal =====================

class ClinicalOverlay(QWidget):
    """
    Overlay principal de gestão clínica.
    
    Mostra três botões: Novo Paciente, Abrir Paciente, Cadastrar Terapeuta.
    Cada botão abre um painel contido no overlay.
    """
    
    session_started = pyqtSignal(str, str, str)  # patient_id, therapist_registro, therapist_nome
    closed = pyqtSignal()
    therapists_changed = pyqtSignal()  # Emitido quando terapeutas são adicionados/alterados
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setObjectName("ClinicalOverlay")
        self._setup_ui()
    
    def _setup_ui(self):
        # Layout principal
        main_layout = QVBoxLayout(self)
        main_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Card central
        self.card = QFrame()
        self.card.setObjectName("SensorCard")
        self.card.setMinimumSize(600, 500)
        self.card.setMaximumSize(800, 700)
        
        # Sombra
        shadow = QGraphicsDropShadowEffect(self.card)
        shadow.setBlurRadius(30)
        shadow.setXOffset(0)
        shadow.setYOffset(5)
        shadow.setColor(QColor(0, 0, 0, 180))
        self.card.setGraphicsEffect(shadow)
        
        card_layout = QVBoxLayout(self.card)
        card_layout.setContentsMargins(0, 0, 0, 0)
        card_layout.setSpacing(0)
        
        # Header com título e botão fechar
        header = QFrame()
        header.setStyleSheet("""
            background-color: #1e1e1e;
            border-top-left-radius: 8px;
            border-top-right-radius: 8px;
            padding: 10px;
        """)
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(16, 10, 16, 10)
        
        self.lbl_title = QLabel("Gestão Clínica")
        self.lbl_title.setStyleSheet("font-size: 16px; font-weight: bold; color: #ffffff;")
        
        self.btn_close = QPushButton("✕")
        self.btn_close.setFixedSize(30, 30)
        self.btn_close.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_close.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #888888;
                border: none;
                font-size: 18px;
            }
            QPushButton:hover {
                color: #ffffff;
            }
        """)
        self.btn_close.clicked.connect(self._on_close)
        
        header_layout.addWidget(self.lbl_title)
        header_layout.addStretch()
        header_layout.addWidget(self.btn_close)
        
        card_layout.addWidget(header)
        
        # Stack para páginas
        self.stack = QStackedWidget()
        card_layout.addWidget(self.stack, 1)
        
        # Página inicial (3 botões)
        self.page_home = self._create_home_page()
        self.stack.addWidget(self.page_home)
        
        # Página Novo Paciente
        self.page_new_patient = NewPatientForm(load_therapists)
        self.page_new_patient.saved.connect(self._on_patient_saved)
        self.page_new_patient.cancelled.connect(self._go_home)
        self.stack.addWidget(self.page_new_patient)
        
        # Página Abrir Paciente
        self.page_open_patient = OpenPatientForm(load_therapists)
        self.page_open_patient.closed.connect(self._go_home)
        self.page_open_patient.session_started.connect(self._on_session_started)
        self.stack.addWidget(self.page_open_patient)
        
        # Página Cadastrar Terapeuta
        self.page_therapist = TherapistForm()
        self.page_therapist.saved.connect(self._on_therapist_saved)
        self.page_therapist.cancelled.connect(self._go_home)
        self.stack.addWidget(self.page_therapist)
        
        main_layout.addWidget(self.card)
    
    def _create_home_page(self) -> QWidget:
        """Cria página inicial com 3 botões grandes."""
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(20)
        
        # Subtítulo
        subtitle = QLabel("Selecione uma opção para começar:")
        subtitle.setStyleSheet("font-size: 14px; color: #aaaaaa; margin-bottom: 10px;")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(subtitle)
        
        layout.addStretch()
        
        # Botões
        btn_style = """
            QPushButton {
                background-color: #2d2d2d;
                color: #ffffff;
                border: 2px solid #3d3d3d;
                border-radius: 8px;
                padding: 20px;
                font-size: 16px;
                font-weight: bold;
                text-align: left;
            }
            QPushButton:hover {
                background-color: #3d3d3d;
                border-color: #4CAF50;
            }
            QPushButton:pressed {
                background-color: #4CAF50;
            }
        """
        
        self.btn_new_patient = QPushButton("  👤  Novo Paciente\n       Cadastrar novo paciente no sistema")
        self.btn_new_patient.setFixedHeight(80)
        self.btn_new_patient.setStyleSheet(btn_style)
        self.btn_new_patient.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_new_patient.clicked.connect(self._open_new_patient)
        
        self.btn_open_patient = QPushButton("  📂  Abrir Paciente\n       Visualizar ou editar paciente existente")
        self.btn_open_patient.setFixedHeight(80)
        self.btn_open_patient.setStyleSheet(btn_style)
        self.btn_open_patient.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_open_patient.clicked.connect(self._open_open_patient)
        
        self.btn_therapist = QPushButton("  🩺  Cadastrar Terapeuta\n       Adicionar novo terapeuta ao sistema")
        self.btn_therapist.setFixedHeight(80)
        self.btn_therapist.setStyleSheet(btn_style)
        self.btn_therapist.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_therapist.clicked.connect(self._open_therapist)
        
        layout.addWidget(self.btn_new_patient)
        layout.addWidget(self.btn_open_patient)
        layout.addWidget(self.btn_therapist)
        
        layout.addStretch()
        
        # Dica
        tip = QLabel("Pressione ESC ou clique no X para fechar")
        tip.setStyleSheet("font-size: 11px; color: #666666;")
        tip.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(tip)
        
        return page
    
    def _open_new_patient(self):
        self.lbl_title.setText("Novo Paciente")
        self.page_new_patient.reset()
        self.stack.setCurrentWidget(self.page_new_patient)
    
    def _open_open_patient(self):
        self.lbl_title.setText("Abrir Paciente")
        self.page_open_patient.refresh()
        self.stack.setCurrentWidget(self.page_open_patient)
    
    def _open_therapist(self):
        self.lbl_title.setText("Cadastrar Terapeuta")
        self.page_therapist.reset()
        self.stack.setCurrentWidget(self.page_therapist)
    
    def _go_home(self):
        self.lbl_title.setText("Gestão Clínica")
        self.stack.setCurrentWidget(self.page_home)
    
    def _on_close(self):
        self._go_home()
        self.closed.emit()
        self.hide()
    
    def _on_patient_saved(self):
        self._go_home()
    
    def _on_therapist_saved(self):
        self.therapists_changed.emit()
        self._go_home()
    
    def _on_session_started(self, patient_id: str, therapist_reg: str, therapist_nome: str):
        self.session_started.emit(patient_id, therapist_reg, therapist_nome)
        self._on_close()
    
    def keyPressEvent(self, event):
        """Permite fechar com ESC."""
        if event.key() == Qt.Key.Key_Escape:
            self._on_close()
        else:
            super().keyPressEvent(event)


# ===================== Widget de Sessão Ativa =====================

class SessionBadge(QFrame):
    """Badge que mostra sessão ativa com timer e controles."""
    
    pause_clicked = pyqtSignal()
    end_clicked = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("SessionBadge")
        self._session: Optional[SessionData] = None
        self._start_time: Optional[datetime] = None
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._update_time)
        self._paused = False
        self._setup_ui()
        self.hide()
    
    def _setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 6, 12, 6)
        layout.setSpacing(12)
        
        self.lbl_info = QLabel("Sessão: --")
        self.lbl_info.setStyleSheet("font-weight: bold;")
        
        self.lbl_time = QLabel("00:00:00")
        self.lbl_time.setStyleSheet("font-family: monospace; font-size: 14px;")
        
        self.btn_pause = QPushButton("⏸")
        self.btn_pause.setFixedSize(28, 28)
        self.btn_pause.setToolTip("Pausar/Retomar")
        self.btn_pause.clicked.connect(self._on_pause)
        
        self.btn_end = QPushButton("⏹")
        self.btn_end.setFixedSize(28, 28)
        self.btn_end.setToolTip("Encerrar Sessão")
        self.btn_end.setStyleSheet("background-color: #b71c1c;")
        self.btn_end.clicked.connect(self._on_end)
        
        layout.addWidget(self.lbl_info)
        layout.addWidget(self.lbl_time)
        layout.addStretch()
        layout.addWidget(self.btn_pause)
        layout.addWidget(self.btn_end)
        
        self.setStyleSheet("""
            #SessionBadge {
                background-color: #1b5e20;
                border-radius: 4px;
                padding: 4px 8px;
            }
        """)
    
    def start_session(self, session: SessionData, patient_name: str = ""):
        """Inicia exibição da sessão."""
        self._session = session
        self._start_time = datetime.now()
        self._paused = False
        
        display_name = patient_name or session.patient_id
        therapist = session.therapist_nome or session.therapist_registro
        self.lbl_info.setText(f"Sessão: {display_name} - {therapist}")
        
        self._timer.start(1000)
        self.show()
    
    def _update_time(self):
        if not self._start_time or self._paused:
            return
        
        delta = datetime.now() - self._start_time
        total_seconds = int(delta.total_seconds())
        hours, remainder = divmod(total_seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        self.lbl_time.setText(f"{hours:02d}:{minutes:02d}:{seconds:02d}")
    
    def _on_pause(self):
        self._paused = not self._paused
        self.btn_pause.setText("▶" if self._paused else "⏸")
        self.pause_clicked.emit()
    
    def _on_end(self):
        self._timer.stop()
        self.end_clicked.emit()
    
    def stop(self):
        """Para o timer e oculta o badge."""
        self._timer.stop()
        self._session = None
        self.hide()
    
    @property
    def current_session(self) -> Optional[SessionData]:
        return self._session
