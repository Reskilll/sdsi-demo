"""
Employee Management System — FastAPI + SQLite + Jinja2
Minimal, production-shaped CRUD app with search, stats, and REST API.
"""

from datetime import date, datetime
from pathlib import Path
from urllib.parse import quote_plus

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from jinja2 import Environment, FileSystemLoader, select_autoescape
from pydantic import BaseModel, Field
from sqlalchemy import create_engine, Column, Integer, String, Date, Float, DateTime, func
from sqlalchemy.orm import declarative_base, sessionmaker

# ---------------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------------
BASE = Path(__file__).resolve().parent
DB_PATH = BASE / "ems.db"
TEMPLATES = BASE / "templates"

app = FastAPI(title="Employee Management System", version="1.0.0")
app.mount("/static", StaticFiles(directory=BASE / "static"), name="static")
env = Environment(loader=FileSystemLoader(str(TEMPLATES)), autoescape=select_autoescape(["html"]))
env.filters["urlencode"] = quote_plus

# Helper: render a template with context + request
def _render(name: str, ctx: dict, status: int = 200) -> HTMLResponse:
    tpl = env.get_template(name)
    return HTMLResponse(tpl.render(ctx), status_code=status)

engine = create_engine(f"sqlite:///{DB_PATH}", connect_args={"check_same_thread": False}, echo=False)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------
class Employee(Base):
    __tablename__ = "employees"

    id = Column(Integer, primary_key=True, autoincrement=True)
    first_name = Column(String(80), nullable=False)
    last_name = Column(String(80), nullable=False)
    email = Column(String(254), unique=True, nullable=False)
    department = Column(String(100), nullable=False)
    position = Column(String(120), nullable=False)
    salary = Column(Float, nullable=False, default=0.0)
    hire_date = Column(Date, nullable=False)
    created_at = Column(DateTime, server_default=func.now())

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"


Base.metadata.create_all(bind=engine)


# ---------------------------------------------------------------------------
# Seed demo data on first run
# ---------------------------------------------------------------------------
def _seed_if_empty():
    db = SessionLocal()
    try:
        if db.query(Employee).count() > 0:
            return
        from datetime import date as _date
        records = [
            ("Priya", "Sharma", "priya.sharma@example.com", "Engineering", "Senior Software Engineer", 115000, _date(2020, 3, 15)),
            ("Arjun", "Patel", "arjun.patel@example.com", "Engineering", "Backend Developer", 95000, _date(2021, 7, 1)),
            ("Mei", "Chen", "mei.chen@example.com", "Engineering", "DevOps Engineer", 100000, _date(2022, 1, 10)),
            ("Sarah", "Johnson", "sarah.j@example.com", "Product", "Product Manager", 120000, _date(2019, 11, 4)),
            ("David", "Kim", "david.kim@example.com", "Product", "UX Designer", 88000, _date(2023, 2, 14)),
            ("Fatima", "Al-Rashid", "fatima.ar@example.com", "Marketing", "Marketing Lead", 95000, _date(2021, 5, 20)),
            ("James", "Wilson", "james.w@example.com", "Marketing", "Content Strategist", 72000, _date(2023, 8, 5)),
            ("Ananya", "Gupta", "ananya.g@example.com", "HR", "HR Manager", 85000, _date(2020, 9, 12)),
            ("Carlos", "Rivera", "carlos.r@example.com", "HR", "Recruiter", 65000, _date(2024, 1, 8)),
            ("Yuki", "Tanaka", "yuki.t@example.com", "Finance", "Financial Analyst", 90000, _date(2022, 4, 22)),
            ("Olivia", "Brown", "olivia.b@example.com", "Finance", "Accountant", 70000, _date(2023, 6, 15)),
            ("Raj", "Verma", "raj.v@example.com", "Engineering", "Frontend Developer", 85000, _date(2024, 3, 1)),
            ("Emma", "Davis", "emma.d@example.com", "Product", "Data Analyst", 82000, _date(2022, 10, 19)),
            ("Alex", "Nguyen", "alex.n@example.com", "Engineering", "QA Engineer", 78000, _date(2023, 4, 30)),
            ("Maria", "Garcia", "maria.g@example.com", "Operations", "Operations Manager", 105000, _date(2019, 6, 1)),
        ]
        for first, last, mail, dept, pos, sal, hdate in records:
            db.add(Employee(first_name=first, last_name=last, email=mail, department=dept, position=pos, salary=sal, hire_date=hdate))
        db.commit()
    finally:
        db.close()


_seed_if_empty()


# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------
class EmployeeIn(BaseModel):
    first_name: str = Field(..., min_length=1, max_length=80)
    last_name: str = Field(..., min_length=1, max_length=80)
    email: str = Field(..., max_length=254)
    department: str = Field(..., max_length=100)
    position: str = Field(..., max_length=120)
    salary: float = Field(..., ge=0)
    hire_date: date


class EmployeeOut(BaseModel):
    id: int
    first_name: str
    last_name: str
    email: str
    department: str
    position: str
    salary: float
    hire_date: date
    created_at: datetime | None = None

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Dependency
# ---------------------------------------------------------------------------
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Web UI routes
# ---------------------------------------------------------------------------
@app.get("/", response_class=HTMLResponse)
def dashboard(request: Request):
    """Landing dashboard with summary stats."""
    db = next(get_db())
    total = db.query(Employee).count()
    dept_counts: list[tuple[str, int]] = (
        db.query(Employee.department, func.count(Employee.id))
        .group_by(Employee.department)
        .order_by(func.count(Employee.id).desc())
        .all()
    )
    avg_team = round(total / len(dept_counts)) if dept_counts else 0
    recent = db.query(Employee).order_by(Employee.created_at.desc()).limit(5).all()
    return _render("dashboard.html", {
        "request": request, "total": total, "dept_counts": dept_counts,
        "avg_team": avg_team, "recent": recent,
    })


@app.get("/employees", response_class=HTMLResponse)
def employee_list(request: Request, search: str = "", dept: str = "", page: int = 1):
    """Paginated employee listing with optional search / department filter."""
    db = next(get_db())
    per_page = 12
    q = db.query(Employee)

    if search:
        term = f"%{search}%"
        q = q.filter(
            (Employee.first_name.ilike(term))
            | (Employee.last_name.ilike(term))
            | (Employee.email.ilike(term))
            | (Employee.position.ilike(term))
        )
    if dept:
        q = q.filter(Employee.department == dept)

    total_count = q.count()
    total_pages = max(1, (total_count + per_page - 1) // per_page)
    page = max(1, min(page, total_pages))
    employees = q.order_by(Employee.last_name).offset((page - 1) * per_page).limit(per_page).all()

    departments = [r[0] for r in db.query(Employee.department).distinct().order_by(Employee.department).all()]

    return _render("employees.html", {
        "request": request, "employees": employees, "search": search, "dept": dept,
        "page": page, "total_pages": total_pages, "total_count": total_count, "departments": departments,
    })


@app.get("/employees/add", response_class=HTMLResponse)
def add_form(request: Request):
    return _render("form.html", {"request": request, "employee": None})


@app.get("/employees/{id}/edit", response_class=HTMLResponse)
def edit_form(request: Request, id: int):
    db = next(get_db())
    emp = db.query(Employee).get(id)
    if not emp:
        raise HTTPException(404, "Employee not found")
    return _render("form.html", {"request": request, "employee": emp})


# ---------------------------------------------------------------------------
# REST API
# ---------------------------------------------------------------------------
@app.get("/api/employees", response_model=list[EmployeeOut])
def api_list(search: str = "", dept: str = ""):
    db = next(get_db())
    q = db.query(Employee)
    if search:
        term = f"%{search}%"
        q = q.filter(
            (Employee.first_name.ilike(term))
            | (Employee.last_name.ilike(term))
            | (Employee.email.ilike(term))
        )
    if dept:
        q = q.filter(Employee.department == dept)
    return q.order_by(Employee.last_name).all()


@app.get("/api/employees/{id}", response_model=EmployeeOut)
def api_get(id: int):
    db = next(get_db())
    emp = db.query(Employee).get(id)
    if not emp:
        raise HTTPException(404, "Employee not found")
    return emp


@app.post("/api/employees", response_model=EmployeeOut, status_code=201)
def api_create(data: EmployeeIn):
    db = next(get_db())
    emp = Employee(**data.model_dump())
    db.add(emp)
    db.commit()
    db.refresh(emp)
    return emp


@app.put("/api/employees/{id}", response_model=EmployeeOut)
def api_update(id: int, data: EmployeeIn):
    db = next(get_db())
    emp = db.query(Employee).get(id)
    if not emp:
        raise HTTPException(404, "Employee not found")
    for k, v in data.model_dump().items():
        setattr(emp, k, v)
    db.commit()
    db.refresh(emp)
    return emp


@app.delete("/api/employees/{id}", status_code=204)
def api_delete(id: int):
    db = next(get_db())
    emp = db.query(Employee).get(id)
    if not emp:
        raise HTTPException(404, "Employee not found")
    db.delete(emp)
    db.commit()


@app.get("/api/stats")
def api_stats():
    db = next(get_db())
    total = db.query(Employee).count()
    depts = (
        db.query(Employee.department, func.count(Employee.id))
        .group_by(Employee.department)
        .order_by(func.count(Employee.id).desc())
        .all()
    )
    avg_salary = db.query(func.avg(Employee.salary)).scalar() or 0
    return {"total_employees": total, "departments": [{"name": d, "count": c} for d, c in depts], "avg_salary": round(avg_salary, 2)}


# ---------------------------------------------------------------------------
# Form submit handler (non-JS fallback)
# ---------------------------------------------------------------------------
@app.post("/employees", response_class=RedirectResponse)
async def create_employee(request: Request):
    form = await request.form()
    db = next(get_db())
    try:
        emp = Employee(
            first_name=str(form["first_name"]),
            last_name=str(form["last_name"]),
            email=str(form["email"]),
            department=str(form["department"]),
            position=str(form["position"]),
            salary=float(form["salary"]),
            hire_date=datetime.strptime(str(form["hire_date"]), "%Y-%m-%d").date(),
        )
        db.add(emp)
        db.commit()
    finally:
        db.close()
    return RedirectResponse("/employees", 303)


@app.post("/employees/{id}", response_class=RedirectResponse)
async def update_employee(request: Request, id: int):
    db = next(get_db())
    try:
        emp = db.query(Employee).get(id)
        if not emp:
            raise HTTPException(404)
        form = await request.form()
        emp.first_name = str(form["first_name"])
        emp.last_name = str(form["last_name"])
        emp.email = str(form["email"])
        emp.department = str(form["department"])
        emp.position = str(form["position"])
        emp.salary = float(form["salary"])
        emp.hire_date = datetime.strptime(str(form["hire_date"]), "%Y-%m-%d").date()
        db.commit()
    finally:
        db.close()
    return RedirectResponse("/employees", 303)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)