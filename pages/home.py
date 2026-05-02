import streamlit as st
from utils.qdrant_stats import get_qdrant_statistics
import plotly.express as px
import pandas as pd

st.markdown('<div class="main-header">📊 Digital Twin Dashboard</div>', unsafe_allow_html=True)

st.markdown("""
    <div style='background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                padding: 1.5rem; 
                border-radius: 10px; 
                color: white; 
                margin-bottom: 2rem;'>
        <h3 style='margin: 0; color: white;'>Welcome to the AI Digital Twin System</h3>
        <p style='margin: 0.5rem 0 0 0; opacity: 0.9;'>Real-time insights and statistics from the Qdrant vector database</p>
    </div>
""", unsafe_allow_html=True)

try:
    stats = get_qdrant_statistics()
    
    # Enhanced metrics with icons
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            label="📦 Total Points",
            value=f"{stats.get('total_points', 0):,}",
            help="Total number of vectors stored in the collection"
        )
    
    with col2:
        st.metric(
            label="🏷️ Unique Labels",
            value=f"{stats.get('unique_labels', 0):,}",
            help="Number of distinct labels in the collection"
        )
    
    with col3:
        st.metric(
            label="📏 Vector Dimension",
            value=f"{stats.get('avg_dim', 0)}",
            help="Average dimension of vectors"
        )
    
    with col4:
        st.metric(
            label="📊 Collection Status",
            value="🟢 Active",
            help="Current status of the Qdrant collection"
        )
    
    st.markdown("---")
    
    # Enhanced visualizations
    col_chart, col_info = st.columns([2, 1])
    
    with col_chart:
        st.subheader("📈 Label Distribution")
        if stats.get("label_distribution"):
            # Convert to DataFrame for better visualization
            df = pd.DataFrame(
                list(stats["label_distribution"].items()),
                columns=["Label", "Count"]
            )
            df = df.sort_values("Count", ascending=False)
            
            # Create interactive bar chart
            fig = px.bar(
                df,
                x="Label",
                y="Count",
                color="Count",
                color_continuous_scale="viridis",
                title="Distribution of Labels in Collection"
            )
            fig.update_layout(
                showlegend=False,
                height=400,
                plot_bgcolor="rgba(0,0,0,0)",
                paper_bgcolor="rgba(0,0,0,0)"
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No label distribution data available")
    
    with col_info:
        st.subheader("ℹ️ Collection Information")
        st.info(f"""
        **Collection Details:**
        
        - **Total Vectors:** {stats.get('total_points', 0):,}
        - **Unique Labels:** {stats.get('unique_labels', 0):,}
        - **Vector Size:** {stats.get('avg_dim', 0)} dimensions
        
        **Status:** ✅ Connected
        """)
        
        if st.button("🔄 Refresh Statistics", use_container_width=True):
            st.rerun()
    
    # Additional insights section
    st.markdown("---")
    st.subheader("💡 Quick Insights")
    
    insight_cols = st.columns(3)
    
    with insight_cols[0]:
        st.markdown("""
            <div style='padding: 1rem; background: #f0f2f6; border-radius: 8px; border-left: 4px solid #667eea;'>
                <h4 style='margin: 0 0 0.5rem 0;'>🔍 Data Quality</h4>
                <p style='margin: 0; color: #666;'>All vectors are properly indexed and searchable</p>
            </div>
        """, unsafe_allow_html=True)
    
    with insight_cols[1]:
        st.markdown("""
            <div style='padding: 1rem; background: #f0f2f6; border-radius: 8px; border-left: 4px solid #764ba2;'>
                <h4 style='margin: 0 0 0.5rem 0;'>⚡ Performance</h4>
                <p style='margin: 0; color: #666;'>Collection is optimized for fast retrieval</p>
            </div>
        """, unsafe_allow_html=True)
    
    with insight_cols[2]:
        st.markdown("""
            <div style='padding: 1rem; background: #f0f2f6; border-radius: 8px; border-left: 4px solid #f093fb;'>
                <h4 style='margin: 0 0 0.5rem 0;'>📊 Analytics</h4>
                <p style='margin: 0; color: #666;'>Real-time statistics updated automatically</p>
            </div>
        """, unsafe_allow_html=True)

except Exception as e:
    st.error(f"❌ Error loading statistics: {str(e)}")
    st.info("""
    **Troubleshooting:**
    1. Check that QDRANT_URL and QDRANT_COLLECTION_NAME are set in your .env file
    2. Ensure the Qdrant server is running and accessible
    3. Verify the collection name exists in your Qdrant instance
    """)