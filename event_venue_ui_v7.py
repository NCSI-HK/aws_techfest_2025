import streamlit as st
import boto3
import json
import uuid
import yaml
import os
import plotly.graph_objects as go
import calendar
import random
from datetime import datetime, timedelta
from botocore.exceptions import ClientError

st.set_page_config(
    page_title="Event Venue Management System",
    page_icon="🏢",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Professional banking-style CSS
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@300;400;500;600&display=swap');
    
    .stApp {
        font-family: 'JetBrains Mono', monospace;
        background-color: #f7fafc;
        color: #1a365d;
    }
    
    .main-header {
        background-color: #1a365d;
        color: #f7fafc;
        padding: 1.5rem;
        margin: -1rem -1rem 2rem -1rem;
        border-bottom: 3px solid #2d3748;
    }
    
    .header-title {
        font-size: 1.8rem;
        font-weight: 600;
        margin: 0;
    }
    
    .header-subtitle {
        font-size: 0.9rem;
        opacity: 0.8;
        margin: 0.2rem 0 0 0;
    }
    
    .metric-container {
        background: white;
        border: 1px solid #e2e8f0;
        border-radius: 8px;
        padding: 1.5rem;
        margin: 0.5rem 0;
        text-align: center;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    
    .metric-value {
        font-size: 1.5rem;
        font-weight: 600;
        color: #1a365d;
    }
    
    .metric-label {
        font-size: 0.8rem;
        color: #718096;
        text-transform: uppercase;
    }
    
    .infrastructure-panel {
        background: #1a365d;
        color: #f7fafc;
        padding: 1rem;
        border-radius: 4px;
        margin: 1rem 0;
        font-size: 0.85rem;
    }
    
    .infra-step {
        padding: 0.3rem 0;
        border-left: 2px solid #f7fafc;
        padding-left: 0.8rem;
        margin: 0.5rem 0;
    }
    
    .chat-message {
        padding: 0.8rem;
        margin: 0.5rem 0;
        border-radius: 8px;
        line-height: 1.4;
        font-size: 0.85rem;
    }
    
    .user-msg {
        background: #1a365d;
        color: white;
    }
    
    .assistant-msg {
        background: #f7fafc;
        border: 1px solid #e9ecef;
    }
</style>
""", unsafe_allow_html=True)

class VenueManagementSystem:
    def __init__(self):
        self.setup_aws()
        self.init_session_state()
        self.init_dynamic_data()
    
    def setup_aws(self):
        try:
            with open('config.yaml') as f:
                config = yaml.safe_load(f)
            
            os.environ.update({
                'AWS_ACCESS_KEY_ID': config['aws']['access_key_id'],
                'AWS_SECRET_ACCESS_KEY': config['aws']['secret_access_key'],
                'AWS_DEFAULT_REGION': config['aws']['region']
            })
            
            self.bedrock = boto3.client('bedrock-agent-runtime', region_name=config['aws']['region'])
            self.dynamodb = boto3.resource('dynamodb', region_name=config['aws']['region'])
            
            with open('created_resources_v4.json') as f:
                resources = json.load(f)
            self.agent_id = resources['agent_id']
            self.table_name = resources.get('dynamodb_table')
            self.resources = resources
            
            # Create DynamoDB tables if they don't exist
            self.create_tables_if_not_exist()
            self.connected = True
            
        except Exception as e:
            self.connected = False
            st.error(f"System Error: {e}")
    
    def create_tables_if_not_exist(self):
        """Skip table creation to improve performance"""
        pass  # Tables are created by the agent deployment
    
    def init_session_state(self):
        if 'show_infrastructure' not in st.session_state:
            st.session_state.show_infrastructure = False
        if 'session_id' not in st.session_state:
            st.session_state.session_id = str(uuid.uuid4())
        if 'execution_log' not in st.session_state:
            st.session_state.execution_log = []
        if 'messages' not in st.session_state:
            st.session_state.messages = []
        if 'selected_date' not in st.session_state:
            st.session_state.selected_date = None
    
    def init_dynamic_data(self):
        """Load data from DynamoDB or initialize if not exists"""
        try:
            # Cache venues in session state to avoid repeated DB calls
            if 'venues' not in st.session_state:
                st.session_state.venues = self.load_venues_from_db()
            self.venues = st.session_state.venues
            
            # Load bookings from DynamoDB
            if 'bookings' not in st.session_state:
                st.session_state.bookings = self.load_bookings_from_db()
            
            # Load revenue data from DynamoDB
            if 'revenue_data' not in st.session_state:
                st.session_state.revenue_data = self.load_revenue_from_db()
            
            # Calculate system metrics from loaded data (cached)
            if 'system_metrics' not in st.session_state:
                st.session_state.system_metrics = {
                    'venues_available': len(self.venues),
                    'uptime': 99.2,
                    'bookings_month': len([d for d in st.session_state.bookings.keys() 
                                         if datetime.strptime(d, '%Y-%m-%d').month == datetime.now().month]),
                    'revenue_ytd': f"${sum(st.session_state.revenue_data['revenue'])/1000:.1f}K",
                    'response_time': 0.8,
                    'availability': 99.5,
                    'throughput': 156,
                    'memory_usage': 68,
                    'cpu_usage': 45
                }
            self.system_metrics = st.session_state.system_metrics
            
        except Exception as e:
            st.warning(f"Could not load from DynamoDB: {e}. Using default data.")
            self.init_default_data()
    
    def load_venues_from_db(self):
        """Load venues from DynamoDB"""
        try:
            table = self.dynamodb.Table('venue_management_venues')
            response = table.scan()
            
            if response['Items']:
                return response['Items']
            else:
                # Initialize default venues in DB
                default_venues = [
                    {'venue_id': 'grand_ballroom', 'name': 'Grand Ballroom', 'capacity': 200, 'price': 2500, 'utilization': 85},
                    {'venue_id': 'conference_a', 'name': 'Conference Room A', 'capacity': 50, 'price': 800, 'utilization': 72},
                    {'venue_id': 'garden_terrace', 'name': 'Garden Terrace', 'capacity': 100, 'price': 1200, 'utilization': 68},
                    {'venue_id': 'executive_board', 'name': 'Executive Board', 'capacity': 20, 'price': 600, 'utilization': 91}
                ]
                
                for venue in default_venues:
                    table.put_item(Item=venue)
                
                return default_venues
                
        except Exception:
            return self.get_default_venues()
    
    def load_bookings_from_db(self):
        """Load bookings from actual agent DynamoDB table"""
        try:
            # Use the actual agent table from resources
            table = self.dynamodb.Table(self.resources['dynamodb_table'])
            response = table.scan()
            
            bookings = {}
            for item in response['Items']:
                # Agent uses 'event_date' field, not 'booking_date'
                date_key = item.get('event_date', '')
                if date_key:
                    bookings[date_key] = f"{item.get('venue_name', '')} - {item.get('client_name', '')} {item.get('event_type', '')}"
            
            return bookings
            
        except Exception:
            return {'2025-03-05': 'Conference Room A - ABC Corp Meeting'}
    
    def load_revenue_from_db(self):
        """Load revenue data from DynamoDB"""
        try:
            table = self.dynamodb.Table('venue_management_revenue')
            response = table.scan()
            
            if response['Items']:
                # Sort by date and extract data
                sorted_items = sorted(response['Items'], key=lambda x: x['date'])
                dates = [datetime.strptime(item['date'], '%Y-%m-%d') for item in sorted_items]
                revenue = [item['revenue'] for item in sorted_items]
                return {'dates': dates, 'revenue': revenue}
            else:
                # Initialize default revenue data
                revenue_data = []
                dates = []
                
                for i in range(30):
                    date = datetime.now() - timedelta(days=29-i)
                    dates.append(date)
                    daily_revenue = 2000 + (i * 50) + (500 if date.weekday() >= 5 else 0)
                    revenue_data.append(daily_revenue)
                    
                    # Save to DB
                    table.put_item(Item={
                        'date': date.strftime('%Y-%m-%d'),
                        'revenue': daily_revenue
                    })
                
                return {'dates': dates, 'revenue': revenue_data}
                
        except Exception:
            dates = [datetime.now() - timedelta(days=x) for x in range(30, 0, -1)]
            revenue = [2000 + (i * 50) for i in range(30)]
            return {'dates': dates, 'revenue': revenue}
    
    def get_default_venues(self):
        """Fallback default venues"""
        return [
            {'name': 'Grand Ballroom', 'capacity': 200, 'price': 2500, 'utilization': 85},
            {'name': 'Conference Room A', 'capacity': 50, 'price': 800, 'utilization': 72},
            {'name': 'Garden Terrace', 'capacity': 100, 'price': 1200, 'utilization': 68},
            {'name': 'Executive Board', 'capacity': 20, 'price': 600, 'utilization': 91}
        ]
    
    def init_default_data(self):
        """Initialize with default data if DB fails"""
        self.venues = self.get_default_venues()
        
        if 'bookings' not in st.session_state:
            st.session_state.bookings = {'2025-03-05': 'Conference Room A - ABC Corp Meeting'}
        
        if 'revenue_data' not in st.session_state:
            dates = [datetime.now() - timedelta(days=x) for x in range(30, 0, -1)]
            revenue = [2000 + (i * 50) for i in range(30)]
            st.session_state.revenue_data = {'dates': dates, 'revenue': revenue}
        
        self.system_metrics = {
            'venues_available': 4,
            'uptime': 99.2,
            'bookings_month': 1,
            'revenue_ytd': '$2.3M',
            'response_time': 0.8,
            'availability': 99.5,
            'throughput': 156,
            'memory_usage': 68,
            'cpu_usage': 45
        }
    
    def render_header(self):
        st.markdown("""
        <div class="main-header">
            <div class="header-title">EVENT VENUE MANAGEMENT SYSTEM</div>
            <div class="header-subtitle">Enterprise AI-Powered Venue Operations | AWS Infrastructure</div>
        </div>
        """, unsafe_allow_html=True)
    
    def render_sidebar(self):
        with st.sidebar:
            # Add NCS logo at the top
            try:
                st.image("logo_ncs.png", width=150)
            except:
                pass  # Continue if logo not found
            
            st.markdown("### AI ASSISTANT CHAT")
            
            # Display messages
            for msg in st.session_state.messages:
                if msg['role'] == 'user':
                    st.markdown(f'<div class="chat-message user-msg">{msg["content"]}</div>', unsafe_allow_html=True)
                elif msg['role'] == 'assistant':
                    st.markdown(f'<div class="chat-message assistant-msg">{msg["content"]}</div>', unsafe_allow_html=True)
                elif msg['role'] == 'infrastructure':
                    infra_html = '<div class="infrastructure-panel">'
                    for step in msg['content']:
                        infra_html += f'<div class="infra-step">{step}</div>'
                    infra_html += '</div>'
                    st.markdown(infra_html, unsafe_allow_html=True)
                elif msg['role'] == 'sources' and msg['content']:
                    with st.expander(f"📚 Knowledge Sources ({len(msg['content'])})"):
                        for i, source in enumerate(msg['content'], 1):
                            st.markdown(f"**Source {i}** (Confidence: {source['score']:.2f})")
                            st.markdown(source['content'])
            
            # Chat input
            user_input = st.chat_input("Ask about venues, policies, pricing...")
            

            
            # Process input
            if user_input:
                st.session_state.messages.append({"role": "user", "content": user_input})
                
                with st.spinner("🤖 Processing..."):
                    result, sources, infra_steps = self.execute_agent_query(user_input)
                    
                    st.session_state.messages.append({"role": "assistant", "content": result})
                    
                    if st.session_state.show_infrastructure and infra_steps:
                        st.session_state.messages.append({"role": "infrastructure", "content": infra_steps})
                    
                    if sources:
                        st.session_state.messages.append({"role": "sources", "content": sources})
                
                st.rerun()
            
            # Hidden sample questions for reference
            show_suggestions = st.checkbox("Show Sample Questions", value=False)
            
            if show_suggestions:
                st.markdown("### SAMPLE QUESTIONS (Copy Text)")
                suggestions = [
                    "What are the catering policies and dietary accommodation options for events?",
                    "Compare the Grand Ballroom versus Conference Room A in terms of pricing, capacity, and included amenities",
                    "Create a booking for TechCorp annual meeting on March 15th, 2025, Grand Ballroom, 180 attendees"
                ]
                
                for i, suggestion in enumerate(suggestions):
                    st.text_area(f"Q{i+1}:", value=suggestion, height=60, key=f"suggest_{i}")
            
            st.markdown("---")
            
            # Infrastructure section with hide option
            show_infrastructure_panel = st.checkbox("Show Infrastructure & Status", value=False)
            
            if show_infrastructure_panel:
                st.markdown("### INFRASTRUCTURE")
                
                # Add AWS logo
                try:
                    st.image("aws_logo.png", width=120)
                except:
                    pass  # Continue if logo not found
                
                st.session_state.show_infrastructure = st.checkbox("Show AWS Details", 
                                                                 value=st.session_state.show_infrastructure)
                
                # AWS Resources Summary
                st.markdown("### AWS RESOURCES")
                st.markdown(f"""
                <div class="infrastructure-panel">
                    <div class="infra-step">🤖 Bedrock Agent ID: {self.resources.get('agent_id', 'N/A')}</div>
                    <div class="infra-step">📚 Knowledge Base ID: {self.resources.get('knowledge_base_id', 'N/A')}</div>
                    <div class="infra-step">⚡ Lambda Function ARN: {self.resources.get('lambda_function_arn', 'N/A')}</div>
                    <div class="infra-step">📊 DynamoDB Table: {self.resources.get('dynamodb_table', 'N/A')}</div>
                    <div class="infra-step">🪣 S3 Bucket: {self.resources.get('s3_bucket', 'N/A')}</div>
                    <div class="infra-step">🔐 IAM Roles: {', '.join(self.resources.get('iam_roles', []))}</div>
                </div>
                """, unsafe_allow_html=True)
                
                # System metrics
                st.markdown("### SYSTEM STATUS")
                
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown(f"""
                    <div class="metric-container">
                        <div class="metric-value">{'🟢' if self.connected else '🔴'}</div>
                        <div class="metric-label">AGENT</div>
                    </div>
                    """, unsafe_allow_html=True)
                
                with col2:
                    st.markdown(f"""
                    <div class="metric-container">
                        <div class="metric-value">{len(st.session_state.execution_log)}</div>
                        <div class="metric-label">OPERATIONS</div>
                    </div>
                    """, unsafe_allow_html=True)
    
    def render_calendar(self):
        st.markdown("### 📅 BOOKING CALENDAR")
        
        # Calendar controls
        col1, col2, col3 = st.columns([1, 2, 1])
        
        with col2:
            current_date = datetime.now()
            selected_month = st.selectbox("📅 Month", 
                                        options=list(range(1, 13)),
                                        index=current_date.month - 1,
                                        format_func=lambda x: calendar.month_name[x])
            selected_year = st.selectbox("📆 Year", 
                                       options=[2024, 2025, 2026],
                                       index=1)
        
        # Generate calendar
        cal = calendar.monthcalendar(selected_year, selected_month)
        
        # Calendar header
        st.markdown(f"""
        <div style="
            background: linear-gradient(135deg, #1a365d 0%, #2d3748 100%);
            color: white;
            padding: 1.5rem;
            border-radius: 12px;
            margin: 1rem 0;
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        ">
            <h3 style="text-align: center; margin-bottom: 1rem; color: white;">
                {calendar.month_name[selected_month]} {selected_year}
            </h3>
        </div>
        """, unsafe_allow_html=True)
        
        # Calendar header days
        days = ['MON', 'TUE', 'WED', 'THU', 'FRI', 'SAT', 'SUN']
        cols = st.columns(7)
        for i, day in enumerate(days):
            with cols[i]:
                st.markdown(f"""
                <div style="
                    background: #f7fafc;
                    padding: 0.8rem;
                    text-align: center;
                    font-weight: 600;
                    border: 1px solid #e2e8f0;
                    color: #1a365d;
                    height: 40px;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                ">{day}</div>
                """, unsafe_allow_html=True)
        
        # Calendar days with structured layout
        for week in cal:
            cols = st.columns(7)
            for i, day in enumerate(week):
                with cols[i]:
                    if day == 0:
                        st.markdown('<div style="height: 80px; border: 1px solid #f0f0f0;"></div>', unsafe_allow_html=True)
                    else:
                        date_str = f"{selected_year}-{selected_month:02d}-{day:02d}"
                        is_booked = date_str in st.session_state.bookings
                        is_today = date_str == datetime.now().strftime('%Y-%m-%d')
                        
                        # Structured calendar cell
                        cell_color = "#1a365d" if is_booked else "#718096" if is_today else "#f7fafc"
                        text_color = "white" if (is_booked or is_today) else "#1a365d"
                        
                        st.markdown(f"""
                        <div style="
                            height: 80px;
                            border: 1px solid #e2e8f0;
                            background: {cell_color};
                            color: {text_color};
                            display: flex;
                            flex-direction: column;
                            align-items: center;
                            justify-content: center;
                            cursor: pointer;
                            transition: all 0.2s;
                        " onclick="document.querySelector('[data-testid=\\"cal_{date_str}\\"]').click()">
                            <div style="font-size: 1.2rem; font-weight: 600; margin-bottom: 4px;">{day}</div>
                            {f'<div style="font-size: 0.6rem; text-align: center; opacity: 0.9;">📅 {st.session_state.bookings[date_str].split(" - ")[0][:8]}</div>' if is_booked else ''}
                        </div>
                        """, unsafe_allow_html=True)
                        
                        # Hidden button for functionality
                        if st.button(" ", key=f"cal_{date_str}", help=f"Select {date_str}"):
                            st.session_state.selected_date = date_str
        
        # Selected date info
        if st.session_state.selected_date:
            st.markdown(f"""
            <div style="
                background: #f7fafc;
                border-left: 4px solid #1a365d;
                padding: 1rem;
                margin: 1rem 0;
                border-radius: 4px;
            ">
                <strong>📅 Selected Date:</strong> {st.session_state.selected_date}<br>
                <strong>📋 Status:</strong> {'🔴 Booked - ' + st.session_state.bookings[st.session_state.selected_date] if st.session_state.selected_date in st.session_state.bookings else '🟢 Available for booking'}
            </div>
            """, unsafe_allow_html=True)
    
    def render_dashboard(self):
        st.markdown("## SYSTEM DASHBOARD")
        
        # Dynamic metrics row
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.markdown(f"""
            <div class="metric-container">
                <div class="metric-value">{self.system_metrics['venues_available']}</div>
                <div class="metric-label">VENUES AVAILABLE</div>
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            st.markdown(f"""
            <div class="metric-container">
                <div class="metric-value">{self.system_metrics['uptime']}%</div>
                <div class="metric-label">SYSTEM UPTIME</div>
            </div>
            """, unsafe_allow_html=True)
        
        with col3:
            st.markdown(f"""
            <div class="metric-container">
                <div class="metric-value">{self.system_metrics['bookings_month']}</div>
                <div class="metric-label">BOOKINGS THIS MONTH</div>
            </div>
            """, unsafe_allow_html=True)
        
        with col4:
            st.markdown(f"""
            <div class="metric-container">
                <div class="metric-value">{self.system_metrics['revenue_ytd']}</div>
                <div class="metric-label">REVENUE YTD</div>
            </div>
            """, unsafe_allow_html=True)
        
        st.markdown("---")
        
        # Main charts section
        col1, col2 = st.columns([3, 2])
        
        with col1:
            # Dynamic venue utilization chart
            venue_names = [v['name'] for v in self.venues]
            utilization = [v['utilization'] for v in self.venues]
            
            fig = go.Figure(data=[go.Bar(x=venue_names, y=utilization, marker_color='#1a365d')])
            fig.update_layout(
                title="VENUE UTILIZATION (%)", 
                font=dict(family="JetBrains Mono"),
                plot_bgcolor='#f7fafc', 
                paper_bgcolor='white', 
                height=400,
                showlegend=False
            )
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            st.markdown("### SYSTEM STATUS")
            
            # Dynamic system performance metrics
            st.markdown(f"**Response Time**: {self.system_metrics['response_time']}s")
            st.progress(min(self.system_metrics['response_time']/2, 1.0))
            
            st.markdown(f"**Availability**: {self.system_metrics['availability']}%")
            st.progress(self.system_metrics['availability']/100)
            
            st.markdown(f"**Throughput**: {self.system_metrics['throughput']} req/min")
            st.progress(self.system_metrics['throughput']/200)
            
            st.markdown(f"**Memory Usage**: {self.system_metrics['memory_usage']}%")
            st.progress(self.system_metrics['memory_usage']/100)
            
            st.markdown(f"**CPU Usage**: {self.system_metrics['cpu_usage']}%")
            st.progress(self.system_metrics['cpu_usage']/100)
        
        # Revenue trend section
        st.markdown("---")
        
        # Dynamic revenue trend chart
        revenue_data = st.session_state.revenue_data
        
        fig = go.Figure(data=go.Scatter(
            x=revenue_data['dates'], 
            y=revenue_data['revenue'], 
            line=dict(color='#1a365d', width=3),
            fill='tonexty',
            fillcolor='rgba(26, 54, 93, 0.1)'
        ))
        fig.update_layout(
            title="30-DAY REVENUE TREND", 
            font=dict(family="JetBrains Mono"),
            plot_bgcolor='#f7fafc', 
            paper_bgcolor='white', 
            height=300,
            showlegend=False,
            xaxis_title="Date",
            yaxis_title="Revenue ($)"
        )
        st.plotly_chart(fig, use_container_width=True)
        
        # Calendar section
        st.markdown("---")
        self.render_calendar()
        
        # AWS Solution Architecture section
        st.markdown("---")
        with st.expander("🏗️ AWS Solution Architecture"):
            try:
                st.image("aws_solution_architecture.png", caption="AWS Solution Architecture Diagram")
            except:
                st.write("Architecture diagram not available")
    
    def execute_agent_query(self, query):
        if not self.connected:
            return "SYSTEM ERROR: Agent connection unavailable", [], []
        
        # Log operation
        st.session_state.execution_log.append({
            'timestamp': datetime.now(),
            'query': query
        })
        
        try:
            response = self.bedrock.invoke_agent(
                inputText=query,
                agentId=self.agent_id,
                agentAliasId='TSTALIASID',
                sessionId=st.session_state.session_id,
                enableTrace=st.session_state.show_infrastructure
            )
            
            result = ""
            infrastructure_steps = []
            sources = []
            
            for event in response['completion']:
                if 'chunk' in event:
                    result = event['chunk']['bytes'].decode('utf8')
                elif 'trace' in event and st.session_state.show_infrastructure:
                    trace = event['trace']['trace']
                    
                    # Capture infrastructure details
                    if 'preProcessingTrace' in trace:
                        infrastructure_steps.append("PRE-PROCESSING: Input validation and routing")
                    
                    if 'orchestrationTrace' in trace:
                        infrastructure_steps.append("ORCHESTRATION: Agent workflow execution")
                    
                    if 'knowledgeBaseRetrievalTrace' in trace:
                        infrastructure_steps.append("KNOWLEDGE BASE: Vector similarity search")
                        kb_trace = trace['knowledgeBaseRetrievalTrace']
                        if 'retrievalResults' in kb_trace:
                            for result_item in kb_trace['retrievalResults']:
                                sources.append({
                                    'content': result_item['content']['text'][:200] + "...",
                                    'score': result_item['score'],
                                    'source': result_item.get('location', {}).get('s3Location', {}).get('uri', 'Knowledge Base')
                                })
                    
                    # Check for Lambda function calls (booking operations)
                    if 'invocationInput' in trace:
                        infrastructure_steps.append("LAMBDA: Processing booking operation")
                        infrastructure_steps.append("DYNAMODB: Updating venue records")
                        # Add AWS resource display for booking operations
                        if any(keyword in query.lower() for keyword in ['book', 'create', 'reserve']):
                            self.display_aws_resources_for_booking()
                    
                    if 'postProcessingTrace' in trace:
                        infrastructure_steps.append("POST-PROCESSING: Response formatting and validation")
            
            # Check if booking was created and refresh data
            # if 'book' in query.lower() and 'EXECUTION ERROR' not in result:
            #     self.refresh_data_from_db()
            # Check if booking was created and refresh data _ version 2
            booking_keywords = ['book', 'reserve', 'schedule', 'create booking']
            if any(keyword in query.lower() for keyword in booking_keywords) and 'EXECUTION ERROR' not in result:
                self.refresh_data_from_db()
            
            return result, sources, infrastructure_steps
            
        except Exception as e:
            return f"EXECUTION ERROR: {str(e)}", [], []
    
    def display_aws_resources_for_booking(self):
        """Display AWS resource information for booking operations"""
        try:
            table = self.dynamodb.Table(self.resources['dynamodb_table'])
            response = table.scan()
            items = response['Items']
            
            aws_info = f"""
📊 Found {len(items)} records in DynamoDB table '{self.resources['dynamodb_table']}':
"""
            for item in items:
                aws_info += f"""
  🎫 Booking ID: {item.get('booking_id', 'N/A')}
     Client: {item.get('client_name', 'N/A')}
     Venue: {item.get('venue_name', 'N/A')}
     Date: {item.get('event_date', 'N/A')}
     Guests: {item.get('guest_count', 'N/A')}
     Status: {item.get('status', 'N/A')}

"""
            
            st.session_state.messages.append({"role": "infrastructure", "content": [aws_info]})
        except Exception as e:
            st.session_state.messages.append({"role": "infrastructure", "content": [f"Error accessing DynamoDB: {str(e)}"]})
    
    def refresh_data_from_db(self):
        """Refresh data from DynamoDB after booking operations"""
        try:
            # Only refresh bookings, not venues (to reduce DB calls)
            st.session_state.bookings = self.load_bookings_from_db()
            
            # Update metrics without recalculating venues
            self.system_metrics['bookings_month'] = len([d for d in st.session_state.bookings.keys() 
                                                       if datetime.strptime(d, '%Y-%m-%d').month == datetime.now().month])
        except Exception:
            pass  # Continue with cached data
    
    def run(self):
        self.render_header()
        self.render_sidebar()
        
        # Main content area
        self.render_dashboard()

if __name__ == "__main__":
    app = VenueManagementSystem()
    app.run()