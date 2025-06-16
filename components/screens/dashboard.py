import streamlit as st
import os
import sys
import json
import streamlit as st
import pandas as pd
import plotly.express as px
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from components.database.propdb import get_all_properties
# Dashboard Page
def dashboard_page():
    st.header("📊 Property Dashboard")
    
    # Get all properties
    properties = get_all_properties()
    
    if not properties:
        st.warning("No properties found in the database.")
        return
    
    # Convert to DataFrame for analysis
    df = pd.DataFrame([dict(prop) for prop in properties])
    df['created_at'] = pd.to_datetime(df['created_at'])
    df['analysis_json'] = df['analysis_json'].apply(json.loads)
    
    # Extract features from analysis_json
    df['property_type'] = df['analysis_json'].apply(lambda x: x.get('property_type', 'Unknown'))
    df['location'] = df['analysis_json'].apply(lambda x: x.get('location', 'Unknown'))
    df['price'] = df['analysis_json'].apply(lambda x: x.get('price', 0))
    df['features'] = df['analysis_json'].apply(lambda x: ', '.join(x.get('features', [])))
    df['amenities'] = df['analysis_json'].apply(lambda x: ', '.join(x.get('amenities', [])))
    
    # Property Statistics
    st.subheader("📈 Property Statistics")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Properties", len(df))
    
    with col2:
        st.metric("Property Types", df['property_type'].nunique())
    
    with col3:
        avg_price = df['price'].mean()
        st.metric("Average Price", f"${avg_price:,.2f}" if avg_price > 0 else "N/A")
    
    with col4:
        latest_prop = df.iloc[0]['property_id']
        st.metric("Latest Property", latest_prop[:8] + "...")
    
    # Property Type Distribution
    st.subheader("🏘️ Property Type Distribution")
    type_counts = df['property_type'].value_counts().reset_index()
    type_counts.columns = ['Property Type', 'Count']
    
    fig1 = px.pie(type_counts, values='Count', names='Property Type', 
                 hole=0.3, color_discrete_sequence=px.colors.sequential.RdBu)
    st.plotly_chart(fig1, use_container_width=True)
    
    # Price Distribution
    if df['price'].sum() > 0:
        st.subheader("💰 Price Distribution")
        fig2 = px.histogram(df, x='price', nbins=20, 
                          labels={'price': 'Price'}, 
                          color_discrete_sequence=['#636EFA'])
        st.plotly_chart(fig2, use_container_width=True)
    
    # Property Timeline
    st.subheader("📅 Property Registration Timeline")
    timeline = df.resample('M', on='created_at').size().reset_index()
    timeline.columns = ['Month', 'Count']
    
    fig3 = px.line(timeline, x='Month', y='Count', 
                  labels={'Count': 'Properties Registered'},
                  markers=True)
    st.plotly_chart(fig3, use_container_width=True)
    
    # Feature Word Cloud (simplified)
    st.subheader("🔍 Most Common Features")
    all_features = ' '.join(df['features'].tolist()).lower()
    features_list = [f.strip() for f in all_features.split(',') if f.strip()]
    features_df = pd.DataFrame(features_list, columns=['feature'])
    top_features = features_df['feature'].value_counts().head(10).reset_index()
    top_features.columns = ['Feature', 'Count']
    
    fig4 = px.bar(top_features, x='Feature', y='Count', 
                 color='Count', color_continuous_scale='Bluered')
    st.plotly_chart(fig4, use_container_width=True)
    
    # Recent Activity
    st.subheader("🔄 Recent Activity")
    recent_properties = df.head(5)[['property_id', 'property_type', 'location', 'created_at']]
    st.dataframe(recent_properties)
    
