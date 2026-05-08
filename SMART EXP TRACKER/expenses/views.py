import csv
import json
from datetime import date, timedelta
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone

from .forms import SignupForm, LoginForm, ExpenseForm
from .models import Expense, predict_category, CATEGORY_CHOICES

# PDF
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.units import inch
import io


# ── Auth ──────────────────────────────────────────────────────────────────────

def signup_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    form = SignupForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        user = form.save()
        login(request, user)
        messages.success(request, f'Welcome, {user.username}! Your account is ready.')
        return redirect('dashboard')
    return render(request, 'auth/signup.html', {'form': form})


def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    form = LoginForm(request, data=request.POST or None)
    if request.method == 'POST' and form.is_valid():
        user = form.get_user()
        login(request, user)
        return redirect('dashboard')
    return render(request, 'auth/login.html', {'form': form})


def logout_view(request):
    logout(request)
    return redirect('login')


# ── Dashboard ─────────────────────────────────────────────────────────────────

@login_required
def dashboard(request):
    today = date.today()
    filter_type = request.GET.get('filter', 'all')

    expenses = Expense.objects.filter(user=request.user)

    if filter_type == 'today':
        expenses = expenses.filter(date=today)
    elif filter_type == 'week':
        start = today - timedelta(days=today.weekday())
        expenses = expenses.filter(date__gte=start)
    elif filter_type == 'month':
        expenses = expenses.filter(date__year=today.year, date__month=today.month)

    total = expenses.aggregate(Sum('amount'))['amount__sum'] or Decimal('0')

    # Category breakdown for chart
    cat_data = {}
    for exp in expenses:
        cat_data[exp.category] = cat_data.get(exp.category, Decimal('0')) + exp.amount

    # Monthly trend (last 6 months)
    monthly = []
    for i in range(5, -1, -1):
        d = today.replace(day=1) - timedelta(days=i * 28)
        amt = Expense.objects.filter(
            user=request.user,
            date__year=d.year,
            date__month=d.month
        ).aggregate(Sum('amount'))['amount__sum'] or 0
        monthly.append({'month': d.strftime('%b %Y'), 'amount': float(amt)})

    context = {
        'expenses': expenses,
        'total': total,
        'filter_type': filter_type,
        'cat_labels': json.dumps(list(cat_data.keys())),
        'cat_values': json.dumps([float(v) for v in cat_data.values()]),
        'monthly_labels': json.dumps([m['month'] for m in monthly]),
        'monthly_values': json.dumps([m['amount'] for m in monthly]),
        'today': today,
    }
    return render(request, 'expenses/dashboard.html', context)


# ── CRUD ──────────────────────────────────────────────────────────────────────

@login_required
def add_expense(request):
    form = ExpenseForm(request.POST or None, initial={'date': date.today()})
    predicted = None

    if request.method == 'POST':
        if form.is_valid():
            expense = form.save(commit=False)
            expense.user = request.user
            expense.save()
            messages.success(request, 'Expense added successfully!')
            return redirect('dashboard')
    return render(request, 'expenses/add_expense.html', {'form': form, 'predicted': predicted})


@login_required
def predict_category_ajax(request):
    desc = request.GET.get('desc', '')
    category = predict_category(desc)
    return JsonResponse({'category': category})


@login_required
def edit_expense(request, pk):
    expense = get_object_or_404(Expense, pk=pk, user=request.user)
    form = ExpenseForm(request.POST or None, instance=expense)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Expense updated!')
        return redirect('dashboard')
    return render(request, 'expenses/edit_expense.html', {'form': form, 'expense': expense})


@login_required
def delete_expense(request, pk):
    expense = get_object_or_404(Expense, pk=pk, user=request.user)
    if request.method == 'POST':
        expense.delete()
        messages.success(request, 'Expense deleted.')
        return redirect('dashboard')
    return render(request, 'expenses/confirm_delete.html', {'expense': expense})


# ── Reports ───────────────────────────────────────────────────────────────────

@login_required
def download_csv(request):
    expenses = Expense.objects.filter(user=request.user)
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="expenses.csv"'
    writer = csv.writer(response)
    writer.writerow(['Date', 'Description', 'Category', 'Amount (₹)', 'Notes'])
    for e in expenses:
        writer.writerow([e.date, e.description, e.category, e.amount, e.notes or ''])
    return response


@login_required
def download_pdf(request):
    expenses = Expense.objects.filter(user=request.user)
    total = expenses.aggregate(Sum('amount'))['amount__sum'] or 0

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=0.5*inch, bottomMargin=0.5*inch)
    styles = getSampleStyleSheet()
    elements = []

    # Title
    title_style = ParagraphStyle('title', parent=styles['Title'],
                                  fontSize=20, textColor=colors.HexColor('#6366f1'), spaceAfter=6)
    elements.append(Paragraph('Smart Expense Tracker — Report', title_style))
    elements.append(Paragraph(f'User: {request.user.username}  |  Generated: {date.today()}', styles['Normal']))
    elements.append(Spacer(1, 0.2*inch))

    # Table
    data = [['Date', 'Description', 'Category', 'Amount (₹)', 'Notes']]
    for e in expenses:
        data.append([str(e.date), e.description, e.category, f'₹{e.amount}', e.notes or ''])
    data.append(['', '', 'TOTAL', f'₹{total}', ''])

    table = Table(data, colWidths=[1*inch, 2.2*inch, 1.2*inch, 1.1*inch, 1.5*inch])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#6366f1')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('ROWBACKGROUNDS', (0, 1), (-1, -2), [colors.HexColor('#f8f9ff'), colors.white]),
        ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#e0e7ff')),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e2e8f0')),
        ('ALIGN', (3, 0), (3, -1), 'RIGHT'),
        ('PADDING', (0, 0), (-1, -1), 6),
    ]))
    elements.append(table)
    doc.build(elements)

    buffer.seek(0)
    response = HttpResponse(buffer, content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="expenses_report.pdf"'
    return response
