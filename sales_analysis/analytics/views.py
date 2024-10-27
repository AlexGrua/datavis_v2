import pandas as pd
import requests
from django.core.files.base import ContentFile
from django.core.files.storage import FileSystemStorage
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login
from django.contrib import messages
import plotly.express as px
from django.conf import settings
from .forms import SalesDataForm, SignUpForm
from .models import SalesData, SharedChart
from django.contrib.auth.views import PasswordResetConfirmView
from django.urls import reverse_lazy, reverse
from django.http import JsonResponse, HttpResponse
from django.shortcuts import get_object_or_404
import uuid
import os
import logging
import plotly.express as px


logger = logging.getLogger(__name__)

def home(request):
    return render(request, 'analytics/home.html')


def register(request):
    if request.method == 'POST':
        form = SignUpForm(request.POST)
        if form.is_valid():
            user = form.save()
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password1')
            user = authenticate(username=username, password=password)
            login(request, user)
            messages.success(request, "Registration successful!")
            return redirect('home')
    else:
        form = SignUpForm()
    return render(request, 'registration/signup.html', {'form': form})


def login_view(request):
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            return redirect('upload')

        messages.error(request, 'Invalid username or password.')

    return render(request, 'registration/login.html')


@login_required
def select_headers(request, file_id):
    """Render the header selection page."""
    return process_file(request, file_id)



class CustomPasswordResetConfirmView(PasswordResetConfirmView):
    template_name = 'registration/password_reset_confirm.html'
    success_url = reverse_lazy('password_reset_complete')


@login_required
def upload_file(request):
    form = SalesDataForm()
    sales_data = SalesData.objects.filter(user=request.user).order_by('-id').first()

    if request.method == 'POST':
        google_sheets_link = request.POST.get('google_sheets_link')
        if google_sheets_link:
            if "/edit?" in google_sheets_link:
                excel_url = google_sheets_link.replace("/edit?", "/export?format=xlsx&")
                try:
                    response = requests.get(excel_url)
                    response.raise_for_status()

                    sales_data = SalesData(user=request.user)
                    sales_data.file.save('fetched_data.xlsx', ContentFile(response.content))
                    sales_data.save()

                    return redirect('process_file', file_id=sales_data.id)

                except Exception as e:
                    messages.error(request, f"Error fetching data from Google Sheets: {str(e)}")
        else:
            form = SalesDataForm(request.POST, request.FILES)
            if form.is_valid():
                sales_data = form.save(commit=False)
                sales_data.user = request.user
                sales_data.save()
                return redirect('process_file', file_id=sales_data.id)
            else:
                messages.error(request, "There was an error with the uploaded form.")

    return render(request, 'analytics/upload.html', {
        'form': form,
        'sales_data': sales_data,
        'file_id': sales_data.id if sales_data else None,  
    })
    


@login_required
def process_file(request, file_id):
    try:
        sales_data = SalesData.objects.get(id=file_id)

        if sales_data.user != request.user:
            messages.error(request, "You are not authorized to view this file.")
            return redirect('upload')

        df = pd.read_excel(sales_data.file)
        headers = df.columns.tolist()
        data = df.values.tolist()  

        if request.method == 'POST':
            selected_headers = request.POST.getlist('selected_headers')

            if not selected_headers:
                messages.error(request, "You must select at least one header for visualization.")
                return render(request, 'analytics/select.html', {
                    'headers': headers,
                    'data': data,
                    'file_id': sales_data.id if sales_data else None,
                })

            request.session['selected_headers'] = selected_headers
            return redirect('charts', file_id=file_id)

        return render(request, 'analytics/select.html', {
            'headers': headers,
            'data': data,  
           
            'file_id': sales_data.id if sales_data else None,
        })
    
    except SalesData.DoesNotExist:
        messages.error(request, "File not found.")
        return redirect('upload')
    except Exception as e:
        messages.error(request, f"An error occurred: {str(e)}")
        return redirect('upload')


@login_required
def charts(request, file_id):

    try:
        sales_data = SalesData.objects.get(id=file_id)

        if sales_data.user != request.user:
            messages.error(request, "You are not authorized to view this file.")
            return redirect('upload')

        df = pd.read_excel(sales_data.file)

        if 'Date' in df.columns:
            df['Date'] = pd.to_datetime(df['Date'], errors='coerce')

        selected_headers = request.session.get('selected_headers', [])

   
        headers = df.columns.tolist()

        if request.method == 'POST':
            selected_visualizations = request.POST.getlist('visualization_type')
            request.session['selected_visualizations'] = selected_visualizations

            graphs = {}
            titles = {}

            if 'line_chart' in selected_visualizations and len(selected_headers) >= 2:
                x_header = selected_headers[0]
                y_header = selected_headers[1]
                if x_header in df.columns and y_header in df.columns:
                    title = f'Line Chart: {y_header} by {x_header}'
                    graphs['line_chart'] = px.line(df, x=x_header, y=y_header,
                                                    title=title,
                                                    width=1200, height=600).update_layout(autosize=True).to_html(full_html=False, include_plotlyjs='cdn')
                    titles['line_chart'] = title

            if 'pie_chart' in selected_visualizations and len(selected_headers) >= 2:
                name_col = selected_headers[0]
                value_col = selected_headers[1]
                title = f'Pie Chart: {value_col} by {name_col}'
                graphs['pie_chart'] = px.pie(df, names=name_col, values=value_col,
                                              title=title,
                                              width=1200, height=600).update_layout(autosize=True).to_html(full_html=False, include_plotlyjs='cdn')
                titles['pie_chart'] = title

            if 'column_chart' in selected_visualizations and len(selected_headers) >= 2:
                x_col = selected_headers[0]
                y_col = selected_headers[1]
                title = f'Column Chart: {y_col} by {x_col}'
                graphs['column_chart'] = px.bar(df, x=x_col, y=y_col,
                                                 title=title,
                                                 width=1200, height=600).update_layout(autosize=True).to_html(full_html=False, include_plotlyjs='cdn')
                titles['column_chart'] = title

            if 'bubble_chart' in selected_visualizations and len(selected_headers) >= 3:
                x_header = selected_headers[0]
                y_header = selected_headers[1]
                size_header = selected_headers[2]
                if x_header in df.columns and y_header in df.columns and size_header in df.columns:
                    title = f'Bubble Chart: {y_header} by {x_header}'
                    graphs['bubble_chart'] = px.scatter(df, x=x_header, y=y_header, size=size_header,
                                                         title=title,
                                                         width=1200, height=600).update_layout(autosize=True).to_html(full_html=False, include_plotlyjs='cdn')
                    titles['bubble_chart'] = title

         
            if 'histogram' in selected_visualizations and len(selected_headers) >= 1:
                value_col = selected_headers[0]
                title = f'Histogram of {value_col}'
                graphs['histogram'] = px.histogram(df, x=value_col,
                                                    title=title,
                                                    width=1200, height=600).update_layout(autosize=True).to_html(full_html=False, include_plotlyjs='cdn')
                titles['histogram'] = title

            if 'pivot_table' in selected_visualizations:
                if len(selected_headers) >= 2:  
                    pivot_table = df.pivot_table(index=selected_headers[0], values=selected_headers[1:], aggfunc='sum').reset_index()
                    pivot_json = pivot_table.to_html(classes='table table-bordered', index=False) 
                    graphs['pivot_table'] = pivot_json  
                    titles['pivot_table'] = 'Pivot Table'

            return render(request, 'analytics/analysis.html', {
                'graphs': graphs,
                'selected_visualizations': selected_visualizations,
                'file_id': file_id,
                'titles': titles,
                'headers': headers,  
            })

        return render(request, 'analytics/charts.html', {
            'selected_headers': selected_headers,
            'file_id': file_id,
            'headers': headers, 
        })

    except SalesData.DoesNotExist:
        messages.error(request, "File not found.")
        return redirect('upload')
    except Exception as e:
        messages.error(request, f"An error occurred: {str(e)}")
        return redirect('upload')



@login_required
def dashboard(request, file_id):
    """Render the dashboard with visualizations based on user selections."""
    try:
        sales_data = SalesData.objects.get(id=file_id)

        if sales_data.user != request.user:
            messages.error(request, "You are not authorized to view this file.")
            return redirect('upload')

        df = pd.read_excel(sales_data.file)

        if 'Date' in df.columns:
            df['Date'] = pd.to_datetime(df['Date'], errors='coerce')

        selected_headers = request.session.get('selected_headers', [])
        selected_visualizations = request.session.get('selected_visualizations', [])

        graphs = {}
        titles = {}


        if selected_visualizations and len(selected_headers) >= 2:
            if 'line_chart' in selected_visualizations:
                x_header = selected_headers[0]
                y_header = selected_headers[1]
                if x_header in df.columns and y_header in df.columns:
                    title = f'Line Chart: {y_header} by {x_header}'
                    graphs['line_chart'] = px.line(df, x=x_header, y=y_header,
                                                    title=title,
                                                    width=1200, height=600).update_layout(autosize=True).to_html(full_html=False, include_plotlyjs='cdn')
                    titles['line_chart'] = title

            if 'pie_chart' in selected_visualizations:
                name_col = selected_headers[0]
                value_col = selected_headers[1]
                title = f'Pie Chart: {value_col} by {name_col}'
                graphs['pie_chart'] = px.pie(df, names=name_col, values=value_col,
                                              title=title,
                                              width=1200, height=600).update_layout(autosize=True).to_html(full_html=False, include_plotlyjs='cdn')
                titles['pie_chart'] = title

            if 'column_chart' in selected_visualizations:
                x_col = selected_headers[0]
                y_col = selected_headers[1]
                title = f'Column Chart: {y_col} by {x_col}'
                graphs['column_chart'] = px.bar(df, x=x_col, y=y_col,
                                                 title=title,
                                                 width=1200, height=600).update_layout(autosize=True).to_html(full_html=False, include_plotlyjs='cdn')
                titles['column_chart'] = title

            if 'bubble_chart' in selected_visualizations and len(selected_headers) >= 3:
                x_header = selected_headers[0]
                y_header = selected_headers[1]
                size_header = selected_headers[2]
                if x_header in df.columns and y_header in df.columns and size_header in df.columns:
                    title = f'Bubble Chart: {y_header} by {x_header}'
                    graphs['bubble_chart'] = px.scatter(df, x=x_header, y=y_header, size=size_header,
                                                         title=title,
                                                         width=1200, height=600).update_layout(autosize=True).to_html(full_html=False, include_plotlyjs='cdn')
                    titles['bubble_chart'] = title

            if 'histogram' in selected_visualizations and len(selected_headers) >= 1:
                value_col = selected_headers[0]
                title = f'Histogram of {value_col}'
                graphs['histogram'] = px.histogram(df, x=value_col,
                                                    title=title,
                                                    width=1200, height=600).update_layout(autosize=True).to_html(full_html=False, include_plotlyjs='cdn')
                titles['histogram'] = title


            if 'pivot_table' in selected_visualizations:
                if len(selected_headers) >= 2:
                    pivot_table = df.pivot_table(index=selected_headers[0], values=selected_headers[1:], aggfunc='sum').reset_index()
                    pivot_json = pivot_table.to_html(classes='table table-striped', index=False) 
                    graphs['pivot_table'] = pivot_json  
                    titles['pivot_table'] = 'Pivot Table' 

            return render(request, 'analytics/analysis.html', {
                'graphs': graphs,
                'selected_visualizations': selected_visualizations,
                'file_id': file_id,
                'titles': titles,
        
            })

    except SalesData.DoesNotExist:
        messages.error(request, "File not found.")
        return redirect('upload')
    except Exception as e:
        messages.error(request, f"An error occurred: {str(e)}")
        return redirect('upload')
    
    return redirect('upload')


def generate_unique_id():
    return str(uuid.uuid4())[:8]


@login_required
def share_chart(request, file_id, chart_type):
    print(f"Chart sharing for File ID: {file_id}, Chart Type: {chart_type}")

    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': "Invalid request method."})

    try:
        sales_data = get_object_or_404(SalesData, id=file_id)

        if sales_data.user != request.user:
            return JsonResponse({'success': False, 'message': "You are not authorized to share this file."})

        selected_visualizations = request.session.get('selected_visualizations', [])
        selected_headers = request.session.get('selected_headers', [])

        if chart_type not in selected_visualizations:
            return JsonResponse({'success': False, 'message': "No visualizations available to share."})

        df = pd.read_excel(sales_data.file)
        fig = None
        chart_filename = None

        # Generate the chart based on the chart_type
        if chart_type == 'line_chart' and len(selected_headers) >= 2:
            x_header = selected_headers[0]
            y_header = selected_headers[1]
            if x_header in df.columns and y_header in df.columns:
                fig = px.line(df, x=x_header, y=y_header,
                              title=f'Line Chart - {y_header} by {x_header}',
                              width=1200, height=600)
                chart_filename = f'line_chart_{file_id}_{generate_unique_id()}.html'

        elif chart_type == 'pie_chart' and len(selected_headers) >= 2:
            name_col = selected_headers[0]
            value_col = selected_headers[1]
            if name_col in df.columns and value_col in df.columns:
                fig = px.pie(df, names=name_col, values=value_col,
                             title=f'Pie Chart - {value_col} by {name_col}',
                             width=1200, height=600)
                chart_filename = f'pie_chart_{file_id}_{generate_unique_id()}.html'

        elif chart_type == 'column_chart' and len(selected_headers) >= 2:
            x_col = selected_headers[0]
            y_col = selected_headers[1]
            if x_col in df.columns and y_col in df.columns:
                fig = px.bar(df, x=x_col, y=y_col,
                             title=f'Column Chart - {y_col} by {x_col}',
                             width=1200, height=600)
                chart_filename = f'column_chart_{file_id}_{generate_unique_id()}.html'

        elif chart_type == 'bubble_chart' and len(selected_headers) >= 3:
            x_header = selected_headers[0]
            y_header = selected_headers[1]
            size_header = selected_headers[2]
            if x_header in df.columns and y_header in df.columns and size_header in df.columns:
                fig = px.scatter(df, x=x_header, y=y_header, size=size_header,
                                 title=f'Bubble Chart - {size_header} by {x_header} and {y_header}',
                                 width=1200, height=600)
                chart_filename = f'bubble_chart_{file_id}_{generate_unique_id()}.html'

        elif chart_type == 'histogram' and len(selected_headers) >= 1:
            value_col = selected_headers[0]
            if value_col in df.columns:
                fig = px.histogram(df, x=value_col,
                                   title=f'Histogram of {value_col}',
                                   width=1200, height=600)
                chart_filename = f'histogram_{file_id}_{generate_unique_id()}.html'

        elif chart_type == 'pivot_table' and len(selected_headers) >= 2:
            x_col = selected_headers[0]
            y_col = selected_headers[1]
            if x_col in df.columns and y_col in df.columns:
                pivot_table_df = df.pivot_table(index=x_col, values=y_col).reset_index()
                pivot_table_html = pivot_table_df.to_html(classes='table table-bordered', index=False)
                return JsonResponse({'success': True, 'pivot_table': pivot_table_html})

        if not fig or not chart_filename:
            return JsonResponse({'success': False, 'message': "Failed to generate the chart."})


        # Save the chart to the filesystem  

        chart_filename = f"{chart_type}_chart_{file_id}_{uuid.uuid4().hex[:8]}.html"  # Example filename generation

        # Create a FileSystemStorage instance
        fs = FileSystemStorage()
        chart_path = os.path.join(settings.MEDIA_ROOT, 'shared_charts', chart_filename)

        # Ensure the directory exists
        os.makedirs(os.path.dirname(chart_path), exist_ok=True)

        # Assuming 'fig' is your chart object that you want to save
        with open(chart_path, 'w') as f:
            f.write(fig.to_html(full_html=False, include_plotlyjs='cdn'))

        # Create a unique ID for the shared chart
        unique_id = str(uuid.uuid4())[:8]
        shared_chart = SharedChart.objects.create(
            user=request.user,
            file_id=file_id,
            chart_type=chart_type,
            unique_id=unique_id
        )

        # Generate the shareable link
        share_link = request.build_absolute_uri(f"/media/shared_charts/{chart_filename}")

        # Optionally, you can also store the share link in the database if needed
        shared_chart.share_link = share_link
        shared_chart.save()

        return JsonResponse({'success': True, 'chart_file_name': chart_filename, 'share_link': share_link})

    except SalesData.DoesNotExist:
        return JsonResponse({'success': False, 'message': "File not found."})
    except Exception as e:
        print(f"Exception: {str(e)}")  
        return JsonResponse({'success': False, 'message': str(e)})

@login_required
def view_shared_chart(request, chart_id, chart_type):
    logger.info(f"Attempting to retrieve SharedChart with Unique ID: {chart_id} and Type: {chart_type}")

    # Retrieve the shared chart object using unique_id
    shared_chart = get_object_or_404(SharedChart, unique_id=chart_id)

    # Generate the chart filename based on the chart type and unique ID
    chart_filename = f'{chart_type}_{shared_chart.file_id}_{shared_chart.unique_id}.html'  
    chart_path = os.path.join(settings.MEDIA_ROOT, 'shared_charts', chart_filename)

    logger.info(f"Chart file path: {chart_path}")

    if not os.path.exists(chart_path):
        logger.error(f"Chart file not found at: {chart_path}")
        messages.error(request, "Chart not found.")
        return render(request, 'analytics/error.html', {'message': 'Chart not found.'})

    try:
        with open(chart_path, 'r') as f:
            chart_html = f.read()
    except IOError as e:
        logger.error(f"Error reading chart file: {str(e)}")
        messages.error(request, "An error occurred while accessing the chart.")
        return redirect('upload')

    return render(request, 'analytics/view_shared_chart.html', {
        'chart_html': chart_html,
        'chart_type': chart_type
    })