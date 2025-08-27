import streamlit as st
import boto3
import json
import uuid
import yaml
import os
import plotly.graph_objects as go
import calendar
from datetime import datetime, timedelta

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
    
    def setup_aws(self):
        try:
            script_dir = os.path.dirname(os.path.abspath(__file__))
            with open(os.path.join(script_dir, 'config.yaml')) as f:
                config = yaml.safe_load(f)
            
            os.environ.update({
                'AWS_ACCESS_KEY_ID': config['aws']['access_key_id'],
                'AWS_SECRET_ACCESS_KEY': config['aws']['secret_access_key'],
                'AWS_DEFAULT_REGION': config['aws']['region']
            })
            
            self.bedrock = boto3.client('bedrock-agent-runtime', region_name=config['aws']['region'])
            self.dynamodb = boto3.resource('dynamodb', region_name=config['aws']['region'])
            
            with open(os.path.join(script_dir, 'created_resources_v4.json')) as f:
                resources = json.load(f)
            self.agent_id = resources['agent_id']
            self.table_name = resources.get('dynamodb_table')
            self.connected = True
            
        except Exception as e:
            self.connected = False
            st.error(f"System Error: {e}")
    
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
        if 'bookings' not in st.session_state:
            st.session_state.bookings = {
                '2025-03-05': 'Conference Room A - ABC Corp',
                '2025-03-12': 'Grand Ballroom - XYZ Event',
                '2025-03-18': 'Garden Terrace - Wedding',
                '2025-03-25': 'Executive Board - Board Meeting'
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
            
            # Handle suggestion selection
            if hasattr(st.session_state, 'selected_query'):
                user_input = st.session_state.selected_query
                del st.session_state.selected_query
            
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
            
            # Suggestion questions with hide option
            show_suggestions = st.checkbox("Show Sample Questions", value=False)
            
            if show_suggestions:
                st.markdown("### SAMPLE QUESTIONS")
                suggestions = [
                    "What are the catering policies and dietary accommodation options for events?",
                    "Compare the Grand Ballroom versus Conference Room A in terms of pricing, capacity, and included amenities",
                    "Create a booking for TechCorp annual meeting on March 15th, 2025, Grand Ballroom, 180 attendees"
                ]
                
                for i, suggestion in enumerate(suggestions):
                    if st.button(f"Q{i+1}", key=f"suggest_{i}", help=suggestion, use_container_width=True):
                        st.session_state.selected_query = suggestion
            
            st.markdown("---")
            
            # Infrastructure section with hide option
            show_infrastructure_panel = st.checkbox("Show Infrastructure & Status", value=False)
            
            if show_infrastructure_panel:
                st.markdown("### INFRASTRUCTURE")
                st.session_state.show_infrastructure = st.checkbox("Show AWS Details", 
                                                                 value=st.session_state.show_infrastructure)
                
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
        
        # Generate calendar with enhanced styling
        cal = calendar.monthcalendar(selected_year, selected_month)
        
        # Calendar with better visual design
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
        
        # Calendar header with better styling
        days = ['MON', 'TUE', 'WED', 'THU', 'FRI', 'SAT', 'SUN']
        cols = st.columns(7)
        for i, day in enumerate(days):
            with cols[i]:
                st.markdown(f"""
                <div style="
                    background: #f7fafc;
                    padding: 0.5rem;
                    text-align: center;
                    font-weight: 600;
                    border: 1px solid #e2e8f0;
                    color: #1a365d;
                ">{day}</div>
                """, unsafe_allow_html=True)
        
        # Calendar days with enhanced styling
        for week in cal:
            cols = st.columns(7)
            for i, day in enumerate(week):
                with cols[i]:
                    if day == 0:
                        st.markdown('<div style="height: 60px;"></div>', unsafe_allow_html=True)
                    else:
                        date_str = f"{selected_year}-{selected_month:02d}-{day:02d}"
                        is_booked = date_str in st.session_state.bookings
                        is_today = date_str == datetime.now().strftime('%Y-%m-%d')
                        
                        # Enhanced button styling
                        button_style = ""
                        if is_booked:
                            button_style = "background: #1a365d; color: white; border: 2px solid #1a365d;"
                        elif is_today:
                            button_style = "background: #718096; color: white; border: 2px solid #718096;"
                        else:
                            button_style = "background: white; color: #1a365d; border: 1px solid #e2e8f0;"
                        
                        if st.button(str(day), key=f"cal_{date_str}"):
                            st.session_state.selected_date = date_str
                        
                        if is_booked:
                            st.markdown(f"""
                            <div style="
                                font-size: 0.7rem;
                                color: #1a365d;
                                text-align: center;
                                padding: 2px;
                                background: #e3f2fd;
                                border-radius: 4px;
                                margin-top: 2px;
                            ">📅 {st.session_state.bookings[date_str].split(' - ')[0]}</div>
                            """, unsafe_allow_html=True)
        
        # Selected date info with better styling
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
                <strong>📋 Status:</strong> {'🔴 ' + st.session_state.bookings[st.session_state.selected_date] if st.session_state.selected_date in st.session_state.bookings else '🟢 Available'}
            </div>
            """, unsafe_allow_html=True)
    
    def render_dashboard(self):
        st.markdown("## SYSTEM DASHBOARD")
        
        # Top metrics row
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.markdown("""
            <div class="metric-container">
                <div class="metric-value">4</div>
                <div class="metric-label">VENUES AVAILABLE</div>
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            st.markdown("""
            <div class="metric-container">
                <div class="metric-value">98.5%</div>
                <div class="metric-label">SYSTEM UPTIME</div>
            </div>
            """, unsafe_allow_html=True)
        
        with col3:
            st.markdown("""
            <div class="metric-container">
                <div class="metric-value">156</div>
                <div class="metric-label">BOOKINGS THIS MONTH</div>
            </div>
            """, unsafe_allow_html=True)
        
        with col4:
            st.markdown("""
            <div class="metric-container">
                <div class="metric-value">$2.3M</div>
                <div class="metric-label">REVENUE YTD</div>
            </div>
            """, unsafe_allow_html=True)
        
        st.markdown("---")
        
        # Main charts section
        col1, col2 = st.columns([3, 2])
        
        with col1:
            # Venue utilization chart
            venues = ['Grand Ballroom', 'Conference A', 'Garden Terrace', 'Executive Board']
            utilization = [85, 72, 68, 91]
            
            fig = go.Figure(data=[go.Bar(x=venues, y=utilization, marker_color='#1a365d')])
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
            
            # System performance metrics
            st.markdown("**Response Time**: 0.8s")
            st.progress(0.92)
            
            st.markdown("**Availability**: 99.2%")
            st.progress(0.992)
            
            st.markdown("**Throughput**: 156 req/min")
            st.progress(0.78)
            
            st.markdown("**Memory Usage**: 68%")
            st.progress(0.68)
            
            st.markdown("**CPU Usage**: 45%")
            st.progress(0.45)
        
        # Revenue trend section
        st.markdown("---")
        
        # Revenue trend chart
        dates = [datetime.now() - timedelta(days=x) for x in range(30, 0, -1)]
        revenue = [2000 + (i * 100) + (i % 7 * 500) for i in range(30)]
        
        fig = go.Figure(data=go.Scatter(
            x=dates, 
            y=revenue, 
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
                    
                    if 'postProcessingTrace' in trace:
                        infrastructure_steps.append("POST-PROCESSING: Response formatting and validation")
            
            return result, sources, infrastructure_steps
            
        except Exception as e:
            return f"EXECUTION ERROR: {str(e)}", [], []
    
    def run(self):
        self.render_header()
        self.render_sidebar()
        
        # Main content area
        self.render_dashboard()

if __name__ == "__main__":
    app = VenueManagementSystem()
    app.run()