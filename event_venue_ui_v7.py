import streamlit as st
import boto3
import json
import uuid
import yaml
import os
import plotly.graph_objects as go
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
    
    .execution-area {
        background: white;
        border: 1px solid #e2e8f0;
        border-radius: 4px;
        padding: 1.5rem;
        min-height: 400px;
    }
    
    .response-box {
        background: #f7fafc;
        border-left: 4px solid #1a365d;
        padding: 1rem;
        margin: 1rem 0;
        font-size: 0.9rem;
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
        if 'current_section' not in st.session_state:
            st.session_state.current_section = 'welcome'
        if 'show_infrastructure' not in st.session_state:
            st.session_state.show_infrastructure = False
        if 'session_id' not in st.session_state:
            st.session_state.session_id = str(uuid.uuid4())
        if 'execution_log' not in st.session_state:
            st.session_state.execution_log = []
    
    def render_header(self):
        st.markdown("""
        <div class="main-header">
            <div class="header-title">EVENT VENUE MANAGEMENT SYSTEM</div>
            <div class="header-subtitle">Enterprise AI-Powered Venue Operations | AWS Infrastructure</div>
        </div>
        """, unsafe_allow_html=True)
    
    def render_sidebar(self):
        with st.sidebar:
            st.markdown("### SYSTEM NAVIGATION")
            
            # Navigation menu
            sections = {
                'welcome': 'DASHBOARD',
                'knowledge': 'KNOWLEDGE BASE',
                'benefits': 'BENEFITS ANALYSIS', 
                'booking': 'BOOKING SYSTEM'
            }
            
            for key, label in sections.items():
                if st.button(label, key=f"nav_{key}", use_container_width=True):
                    st.session_state.current_section = key
            
            st.markdown("---")
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
    
    def render_welcome_dashboard(self):
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
            height=350,
            showlegend=False,
            xaxis_title="Date",
            yaxis_title="Revenue ($)"
        )
        st.plotly_chart(fig, use_container_width=True)
        
        # Action selection
        st.markdown("---")
        st.markdown("## SELECT OPERATION MODE")
        self.render_action_menu()
    
    def render_action_menu(self):
        col1, col2 = st.columns([1, 3])
        
        with col1:
            st.markdown("**OPERATIONS MENU**")
            
            if st.button("→ Knowledge Base", key="kb_menu", use_container_width=True):
                st.session_state.current_section = 'knowledge'
            if st.button("→ Benefits Analysis", key="benefits_menu", use_container_width=True):
                st.session_state.current_section = 'benefits'
            if st.button("→ Booking System", key="booking_menu", use_container_width=True):
                st.session_state.current_section = 'booking'
        
        with col2:
            st.markdown("**OPERATION DETAILS**")
            st.markdown("""
            - **Knowledge Base**: Access comprehensive venue documentation and policies
            - **Benefits Analysis**: Compare venues, pricing tiers, and service packages  
            - **Booking System**: Full reservation management with real-time availability
            """)
    
    def execute_agent_query(self, query, operation_type):
        if not self.connected:
            return "SYSTEM ERROR: Agent connection unavailable", [], []
        
        # Log operation
        st.session_state.execution_log.append({
            'timestamp': datetime.now(),
            'operation': operation_type,
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
    
    def render_execution_interface(self, section_type):
        queries = {
            'knowledge': "What are the catering policies and dietary accommodation options for events?",
            'benefits': "Compare the Grand Ballroom versus Conference Room A in terms of pricing, capacity, and included amenities",
            'booking': "Create a booking for TechCorp annual meeting on March 15th, 2025, Grand Ballroom, 180 attendees"
        }
        
        st.markdown(f"## {section_type.upper()} OPERATION INTERFACE")
        
        # Query input
        query = st.text_area("OPERATION QUERY:", value=queries.get(section_type, ""), height=100)
        
        col1, col2 = st.columns([3, 1])
        
        with col1:
            if st.button(f"EXECUTE {section_type.upper()} OPERATION", type="primary"):
                with st.spinner("PROCESSING..."):
                    result, sources, infra_steps = self.execute_agent_query(query, section_type)
                    
                    # Display result
                    st.markdown("### OPERATION RESULT")
                    st.markdown(f'<div class="response-box">{result}</div>', unsafe_allow_html=True)
                    
                    # Show infrastructure if enabled
                    if st.session_state.show_infrastructure and infra_steps:
                        st.markdown("### AWS INFRASTRUCTURE EXECUTION")
                        infra_html = '<div class="infrastructure-panel">'
                        for step in infra_steps:
                            infra_html += f'<div class="infra-step">{step}</div>'
                        infra_html += '</div>'
                        st.markdown(infra_html, unsafe_allow_html=True)
                    
                    # Show sources if available
                    if sources:
                        with st.expander(f"KNOWLEDGE SOURCES ({len(sources)} found)"):
                            for i, source in enumerate(sources, 1):
                                st.markdown(f"**Source {i}** (Confidence: {source['score']:.2f})")
                                st.markdown(source['content'])
        
        with col2:
            st.markdown("### OPERATION LOG")
            for log_entry in reversed(st.session_state.execution_log[-5:]):
                st.markdown(f"**{log_entry['timestamp'].strftime('%H:%M:%S')}**")
                st.markdown(f"{log_entry['operation'].upper()}")
                st.markdown("---")
    
    def run(self):
        self.render_header()
        self.render_sidebar()
        
        # Main content area
        if st.session_state.current_section == 'welcome':
            self.render_welcome_dashboard()
        elif st.session_state.current_section in ['knowledge', 'benefits', 'booking']:
            self.render_execution_interface(st.session_state.current_section)

if __name__ == "__main__":
    app = VenueManagementSystem()
    app.run()