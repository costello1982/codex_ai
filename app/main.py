from __future__ import annotations

from datetime import datetime
from ipaddress import ip_network
from typing import Optional

from fastapi import Depends, FastAPI, Form, HTTPException, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from starlette.middleware.sessions import SessionMiddleware

from .auth import get_current_user, get_password_hash, verify_password
from .database import Base, SessionLocal, engine, get_db
from .models import IPAddress, Subnet, User

app = FastAPI(title="IPAM", version="1.0.0")
app.add_middleware(SessionMiddleware, secret_key="super-secret-session-key")
app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")
templates.env.globals['now'] = datetime.utcnow

@app.on_event("startup")
def on_startup() -> None:
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        if not db.query(User).filter_by(username="admin").first():
            user = User(username="admin", hashed_password=get_password_hash("changeme"))
            db.add(user)
            db.commit()


def next_available_ip(subnet: Subnet) -> Optional[str]:
    used = {ip.address for ip in subnet.ip_addresses}
    for host in subnet.hosts:
        if host not in used:
            return host
    return None


@app.get("/", include_in_schema=False)
def index(request: Request):
    if request.session.get("user_id"):
        return RedirectResponse("/dashboard", status_code=status.HTTP_303_SEE_OTHER)
    return RedirectResponse("/login", status_code=status.HTTP_303_SEE_OTHER)


@app.get("/login", response_class=HTMLResponse)
def login_page(request: Request, message: Optional[str] = None):
    return templates.TemplateResponse(
        "login.html", {"request": request, "message": message}
    )


@app.post("/login")
def login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.username == username).first()
    if not user or not verify_password(password, user.hashed_password):
        return templates.TemplateResponse(
            "login.html",
            {
                "request": request,
                "message": "Invalid credentials. Try again.",
                "username": username,
            },
            status_code=status.HTTP_401_UNAUTHORIZED,
        )
    request.session["user_id"] = user.id
    return RedirectResponse("/dashboard", status_code=status.HTTP_303_SEE_OTHER)


@app.get("/logout")
def logout(request: Request):
    request.session.pop("user_id", None)
    return RedirectResponse("/login", status_code=status.HTTP_303_SEE_OTHER)


@app.get("/dashboard", response_class=HTMLResponse)
def dashboard(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    subnets = db.query(Subnet).order_by(Subnet.cidr).all()
    for subnet in subnets:
        subnet.ip_addresses  # Ensure relationship is loaded for templates
    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "user": user,
            "subnets": subnets,
        },
    )


@app.get("/calculator", response_class=HTMLResponse)
def calculator_form(
    request: Request, user: User = Depends(get_current_user), cidr: Optional[str] = None
):
    details = None
    error = None
    if cidr:
        try:
            network = ip_network(cidr, strict=False)
            usable = (
                network.num_addresses
                if network.prefixlen >= 31
                else max(network.num_addresses - 2, 0)
            )
            if network.prefixlen >= 31:
                first_host = str(network.network_address)
                last_host = str(network.broadcast_address)
            else:
                hosts_iter = network.hosts()
                first_host = str(next(hosts_iter))
                last_host = str(network.broadcast_address - 1)
            details = {
                "network": str(network.network_address),
                "broadcast": str(network.broadcast_address),
                "netmask": str(network.netmask),
                "wildcard": str(network.hostmask),
                "hosts": usable,
                "cidr": str(network),
                "first_host": first_host,
                "last_host": last_host,
            }
        except ValueError:
            error = "Invalid CIDR provided"
    return templates.TemplateResponse(
        "calculator.html",
        {"request": request, "user": user, "details": details, "error": error},
    )


@app.get("/subnets/new", response_class=HTMLResponse)
def new_subnet_form(
    request: Request,
    user: User = Depends(get_current_user),
    cidr: Optional[str] = None,
    description: Optional[str] = None,
    error: Optional[str] = None,
):
    return templates.TemplateResponse(
        "new_subnet.html",
        {
            "request": request,
            "user": user,
            "cidr": cidr or "",
            "description": description or "",
            "error": error,
        },
    )


@app.post("/subnets")
def create_subnet(
    request: Request,
    cidr: str = Form(...),
    description: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    try:
        network = ip_network(cidr, strict=False)
    except ValueError:
        return new_subnet_form(
            request,
            user=user,
            cidr=cidr,
            description=description,
            error="Invalid CIDR notation.",
        )

    subnet = Subnet(cidr=str(network), description=description, owner=user)
    db.add(subnet)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        return new_subnet_form(
            request,
            user=user,
            cidr=cidr,
            description=description,
            error="Subnet already exists.",
        )
    return RedirectResponse(
        f"/subnets/{subnet.id}", status_code=status.HTTP_303_SEE_OTHER
    )


@app.get("/subnets/{subnet_id}", response_class=HTMLResponse)
def subnet_detail(
    request: Request,
    subnet_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    message: Optional[str] = None,
    error: Optional[str] = None,
):
    subnet = db.get(Subnet, subnet_id)
    if subnet is None:
        raise HTTPException(status_code=404, detail="Subnet not found")
    subnet.ip_addresses
    subnet.owner
    return templates.TemplateResponse(
        "subnet_detail.html",
        {
            "request": request,
            "user": user,
            "subnet": subnet,
            "message": message,
            "error": error,
        },
    )


@app.post("/subnets/{subnet_id}/allocate")
def allocate_ip(
    request: Request,
    subnet_id: int,
    ip_address_value: Optional[str] = Form(None),
    hostname: Optional[str] = Form(None),
    allocated_to: Optional[str] = Form(None),
    notes: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    subnet = db.get(Subnet, subnet_id)
    if subnet is None:
        raise HTTPException(status_code=404, detail="Subnet not found")

    subnet.ip_addresses
    target_ip = ip_address_value.strip() if ip_address_value else None
    if target_ip:
        if not subnet.is_valid_host(target_ip):
            return subnet_detail(
                request,
                subnet_id,
                db,
                user,
                error="Provided IP is not a usable host in this subnet.",
            )
        if any(ip.address == target_ip for ip in subnet.ip_addresses):
            return subnet_detail(
                request,
                subnet_id,
                db,
                user,
                error="IP address already allocated.",
            )
    else:
        target_ip = next_available_ip(subnet)
        if target_ip is None:
            return subnet_detail(
                request,
                subnet_id,
                db,
                user,
                error="No available IP addresses left in this subnet.",
            )

    record = IPAddress(
        address=target_ip,
        hostname=hostname or None,
        allocated_to=allocated_to or None,
        notes=notes or None,
        subnet=subnet,
        status="allocated",
    )
    db.add(record)
    db.commit()
    return RedirectResponse(
        f"/subnets/{subnet_id}?message=Allocated+{target_ip}",
        status_code=status.HTTP_303_SEE_OTHER,
    )


@app.post("/subnets/{subnet_id}/release/{ip_id}")
def release_ip(
    subnet_id: int,
    ip_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    record = db.get(IPAddress, ip_id)
    if record is None or record.subnet_id != subnet_id:
        raise HTTPException(status_code=404, detail="Allocation not found")
    db.delete(record)
    db.commit()
    return RedirectResponse(
        f"/subnets/{subnet_id}?message=Released+{record.address}",
        status_code=status.HTTP_303_SEE_OTHER,
    )


@app.post("/subnets/{subnet_id}/delete")
def delete_subnet(
    subnet_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    subnet = db.get(Subnet, subnet_id)
    if subnet is None:
        raise HTTPException(status_code=404, detail="Subnet not found")
    db.delete(subnet)
    db.commit()
    return RedirectResponse("/dashboard", status_code=status.HTTP_303_SEE_OTHER)
