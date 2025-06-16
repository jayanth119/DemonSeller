import streamlit as st
import os
import sys
import json
import io
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from components.database.propdb import get_property_from_db, get_property_images, get_property_videos
from components.utils.emailUtil import share_property_results
# Property Search Page
def search_properties_page(search_agent):
    st.header("🔍 Search Properties")
    
    # Search input section
    query = st.text_input("Search Query", 
                         placeholder="e.g., Flats contains of no ac, not having elevator and Newly renovated",
                         help="Use natural language to describe what you're looking for")
    
    col1, col2 = st.columns([3, 1])
    with col1:
        search_button = st.button("🔍 Search Properties", type="primary")
    with col2:
        max_results = st.selectbox("Max Results", [1, 2, 3, 5, 10, 15, 20], index=0)
    
    # Advanced search options
    with st.expander("🔧 Advanced Search Options"):
        include_images = st.checkbox("Display Images", value=True)
        show_full_analysis = st.checkbox("Show Full Analysis Data", value=False)
        show_file_details = st.checkbox("Show Detailed File Information", value=False)
    
    if search_button:
        if not query.strip():
            st.warning("⚠️ Please enter a search query.")
        else:
            with st.spinner("🔍 Searching properties..."):
                try:
                    results = search_agent.search(query.strip(), k=max_results)
                    processed_results = []
                    
                    for result in results:
                        property_id = result.get('property_id', 'unknown')
                        score = result.get('score', 0.0)
                        matched_features = result.get('matched_features', [])
                        missing_features = result.get('missing_features', [])
                        feature_match_percentage = result.get('feature_match_percentage', 0)
                        
                        # Get property from database
                        property_data = get_property_from_db(property_id)
                        images = get_property_images(property_id)
                        videos = get_property_videos(property_id)
                        
                        processed_result = {
                            'property_id': property_id,
                            'score': score,
                            'matched_features': matched_features,
                            'missing_features': missing_features,
                            'feature_match_percentage': feature_match_percentage,
                            'property_data': dict(property_data) if property_data else None,
                            'images': images,
                            'videos': videos
                        }
                        
                        processed_results.append(processed_result)
                    
                    st.session_state.search_results = processed_results
                    st.session_state.search_query = query
                    st.session_state.email_sent = False
                    st.session_state.email_status = None
                    
                    if processed_results:
                        st.success(f"🏠 Found {len(processed_results)} matching properties")
                
                except Exception as e:
                    st.error(f"❌ Error during search: {str(e)}")
                    st.session_state.search_results = None

    # Display results if they exist in session state
    if st.session_state.search_results:
        results = st.session_state.search_results
        query = st.session_state.search_query or "Previous search"
        
        if not search_button:
            st.success(f"🏠 Showing {len(results)} properties from your search")
        
        # Share functionality section
        st.markdown("---")
        st.subheader("📤 Share Results")
        
        if st.session_state.email_sent and st.session_state.email_status:
            if st.session_state.email_status['success']:
                st.success(f"✅ **Email sent successfully!**")
                st.success(f"📧 Property details have been shared with **{st.session_state.email_status['recipient']}**")
            else:
                st.error("❌ **Failed to send email**")
        
        share_col1, share_col2, share_col3 = st.columns([2, 2, 1])
        
        with share_col1:
            recipient_email = st.text_input("📧 Recipient Email", 
                                         placeholder="Enter email address",
                                         help="Email address to send the property details",
                                         key="recipient_email_input")
        
        with share_col2:
            property_options = [f"Property {i+1}: {result['property_id'][:12]}..." for i, result in enumerate(results)]
            selected_properties = st.multiselect("🏠 Select Properties to Share", 
                                             property_options,
                                             default=property_options,
                                             key="property_selection")
        
        with share_col3:
            st.write("")
            st.write("")
            share_button = st.button("📤 Share Results", type="secondary", key="share_button")
        
        if share_button:
            if not recipient_email.strip():
                st.warning("⚠️ Please enter a recipient email address.")
            elif not selected_properties:
                st.warning("⚠️ Please select at least one property to share.")
            else:
                selected_indices = [property_options.index(prop) for prop in selected_properties]
                selected_results = [results[i] for i in selected_indices]
                
                with st.spinner("📤 Sending email..."):
                    share_success = share_property_results(
                        query=query,
                        results=selected_results,
                        recipient_email=recipient_email,
                        include_images=include_images
                    )
                
                if share_success:
                    st.session_state.email_sent = True
                    st.session_state.email_status = {
                        'success': True,
                        'recipient': recipient_email,
                        'count': len(selected_results)
                    }
                    st.balloons()
                else:
                    st.session_state.email_sent = True
                    st.session_state.email_status = {
                        'success': False,
                        'error': 'Failed to send email'
                    }
                
                st.rerun()
        
        st.markdown("---")
        
        # Display results
        for i, result in enumerate(results, 1):
            property_id = result['property_id']
            score = result['score']
            matched_features = result['matched_features']
            missing_features = result['missing_features']
            feature_match_percentage = result['feature_match_percentage']
            property_data = result['property_data']
            images = result['images']
            videos = result['videos']
            
            with st.expander(f"🏠 Property {i}: {property_id[:8]}... (Score: {score:.3f}, Match: {feature_match_percentage}%)", expanded=True):
                
                col_a, col_b, col_c = st.columns(3)
                with col_a:
                    st.metric("Property ID", property_id[:8] + "...")
                    st.write(f"**Full ID:** `{property_id}`")
                with col_b:
                    st.metric("Match Score", f"{score:.3f}")
                    st.metric("Feature Match", f"{feature_match_percentage}%")
                with col_c:
                    st.metric("Images", len(images))
                    st.metric("Videos", len(videos))
                
                # Feature matching section
                if matched_features or missing_features:
                    st.subheader("🎯 Feature Analysis")
                    
                    if matched_features:
                        st.success("✅ **Matched Features:**")
                        for feature in matched_features:
                            st.write(f"• {feature}")
                    
                    if missing_features:
                        st.warning("❌ **Missing Features:**")
                        for feature in missing_features:
                            st.write(f"• {feature}")
                
                # Media display section
                if images:
                    st.subheader("📁 Property Media")
                    
                    if include_images:
                        st.write("**📸 Images:**")
                        cols = st.columns(3)
                        for idx, img in enumerate(images):
                            with cols[idx % 3]:
                                st.image(io.BytesIO(img['image_data']), caption=img['image_name'], use_column_width=True)
                
                # Property Analysis Data
                if property_data:
                    st.subheader("📊 Property Analysis")
                    
                    if 'description' in property_data:
                        st.write("**📝 Original Description:**")
                        with st.container():
                            st.text_area("", 
                                       value=property_data['description'], 
                                       height=100, 
                                       disabled=True, 
                                       key=f"desc_{i}_{property_id}")
                    
                    if show_full_analysis:
                        st.write("**🔍 Full Analysis Data:**")
                        st.json(json.loads(property_data['analysis_json']))
                    else:
                        analysis_data = json.loads(property_data['analysis_json'])
                        summary_keys = ['property_type', 'location', 'price', 'features', 'amenities', 'condition']
                        summary_data = {k: v for k, v in analysis_data.items() if k in summary_keys and v}
                        if summary_data:
                            st.write("**📋 Key Features:**")
                            st.json(summary_data)
                
                # Show file listing if enabled
                if show_file_details:
                    st.subheader("📂 File Details")
                    file_col1, file_col2, file_col3 = st.columns(3)
                    
                    with file_col1:
                        if images:
                            st.write("**📸 Image Files:**")
                            for img in images:
                                st.write(f"• {img['image_name']}")
                    
                    with file_col3:
                        if property_data:
                            st.write("**📄 Text Files:**")
                            st.write("• description.txt")
                            st.write("• analysis.json")
                
                st.markdown("---")
    else:
        st.info("🔍 No matching properties found. Try adjusting your search terms.")
        
        st.subheader("💡 Search Suggestions")
        st.write("Try searching for:")
        suggestions = [
            "apartment with balcony",
            "house with parking",
            "no AC no elevator",
            "newly renovated",
            "furnished flat",
            "WiFi included"
        ]
        
        suggestion_cols = st.columns(3)
        for idx, suggestion in enumerate(suggestions):
            with suggestion_cols[idx % 3]:
                if st.button(f"🔍 {suggestion}", key=f"suggest_{suggestion}"):
                    st.session_state.suggested_query = suggestion
                    st.rerun()