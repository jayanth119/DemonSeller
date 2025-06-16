def share_property_results(query, results, recipient_email, include_images=True):
    """
    Function to share property search results via email
    
    Args:
        query (str): Original search query
        results (list): List of property results to share
        recipient_email (str): Email address to send the results to
        include_images (bool): Whether to include images in the email
    
    Returns:
        bool: True if sharing was successful, False otherwise
    """
    try:
        import smtplib
        from email.mime.multipart import MIMEMultipart
        from email.mime.text import MIMEText
        from email.mime.image import MIMEImage
        import os
        from datetime import datetime
        
        # Email configuration (you'll need to set these up based on your email service)
        # You should store these in environment variables or config file
        SMTP_SERVER = "smtp.gmail.com"  # Change based on your email provider
        SMTP_PORT = 587
        SENDER_EMAIL = "jayanthunofficial@gmail.com"  # Your app's email
        SENDER_PASSWORD = "qxhx qwhd aobk xgqf"  # App password or OAuth token
        
        # Create message
        msg = MIMEMultipart('alternative')
        msg['From'] = SENDER_EMAIL
        msg['To'] = recipient_email
        msg['Subject'] = f"Property Search Results: {query}"
        
        # Create HTML email content
        html_content = f"""
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                .header {{ background-color: #f0f2f6; padding: 20px; border-radius: 10px; margin-bottom: 20px; }}
                .property {{ border: 1px solid #ddd; margin: 20px 0; padding: 20px; border-radius: 10px; }}
                .property-header {{ background-color: #e8f4fd; padding: 15px; border-radius: 5px; margin-bottom: 15px; }}
                .features {{ margin: 10px 0; }}
                .matched {{ color: #28a745; }}
                .missing {{ color: #dc3545; }}
                .metrics {{ display: flex; justify-content: space-around; margin: 15px 0; }}
                .metric {{ text-align: center; }}
                .images {{ margin: 15px 0; }}
                img {{ max-width: 200px; margin: 5px; border-radius: 5px; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h2>🏠 Property Search Results</h2>
                <p><strong>Search Query:</strong> {query}</p>
                <p><strong>Results Found:</strong> {len(results)} properties</p>
                <p><strong>Generated on:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            </div>
        """
        
        # Add each property to the email
        for i, result in enumerate(results, 1):
            property_id = result['property_id']
            score = result['score']
            matched_features = result['matched_features']
            missing_features = result['missing_features']
            feature_match_percentage = result['feature_match_percentage']
            folder_info = result['folder_info']
            
            html_content += f"""
            <div class="property">
                <div class="property-header">
                    <h3>Property {i}: {property_id[:12]}...</h3>
                    <div class="metrics">
                        <div class="metric">
                            <strong>Match Score</strong><br>
                            {score:.3f}
                        </div>
                        <div class="metric">
                            <strong>Feature Match</strong><br>
                            {feature_match_percentage}%
                        </div>
                        <div class="metric">
                            <strong>Images</strong><br>
                            {len(folder_info.get('images', []))}
                        </div>
                    </div>
                </div>
                
                <p><strong>Full Property ID:</strong> {property_id}</p>
            """
            
            # Add property description if available
            if folder_info.get('profile_data') and 'description' in folder_info['profile_data']:
                html_content += f"""
                <h4>📝 Description:</h4>
                <p>{folder_info['profile_data']['description']}</p>
                """
            
            # Add matched features
            if matched_features:
                html_content += f"""
                <div class="features">
                    <h4 class="matched">✅ Matched Features:</h4>
                    <ul class="matched">
                """
                for feature in matched_features:
                    html_content += f"<li>{feature}</li>"
                html_content += "</ul></div>"
            
            # Add missing features
            if missing_features:
                html_content += f"""
                <div class="features">
                    <h4 class="missing">❌ Missing Features:</h4>
                    <ul class="missing">
                """
                for feature in missing_features:
                    html_content += f"<li>{feature}</li>"
                html_content += "</ul></div>"
            
            # Add key property features if available
            if folder_info.get('profile_data'):
                analysis_data = folder_info['profile_data']
                if isinstance(analysis_data, dict):
                    summary_keys = ['property_type', 'location', 'price', 'features', 'amenities', 'condition']
                    summary_data = {k: v for k, v in analysis_data.items() if k in summary_keys and v}
                    if summary_data:
                        html_content += "<h4>📋 Key Features:</h4><ul>"
                        for key, value in summary_data.items():
                            html_content += f"<li><strong>{key.replace('_', ' ').title()}:</strong> {value}</li>"
                        html_content += "</ul>"
            
            html_content += "</div>"
        
        html_content += """
            <div class="header" style="margin-top: 30px;">
                <p><em>This email was generated automatically from your property search application.</em></p>
                <p>If you have any questions about these properties, please contact the sender.</p>
            </div>
        </body>
        </html>
        """
        
        # Attach HTML content
        html_part = MIMEText(html_content, 'html')
        msg.attach(html_part)
        
        # Attach images if requested and available
        if include_images:
            image_count = 0
            for result in results:
                folder_info = result['folder_info']
                if folder_info.get('image_paths'):
                    for img_path in folder_info['image_paths'][:3]:  # Limit to 3 images per property
                        try:
                            if os.path.exists(img_path):
                                with open(img_path, 'rb') as f:
                                    img_data = f.read()
                                image = MIMEImage(img_data)
                                image.add_header('Content-Disposition', f'attachment; filename=property_{result["property_id"][:8]}_{image_count}.jpg')
                                msg.attach(image)
                                image_count += 1
                        except Exception as e:
                            print(f"Error attaching image {img_path}: {e}")
                            continue
        
        # Send email
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(SENDER_EMAIL, SENDER_PASSWORD)
            text = msg.as_string()
            server.sendmail(SENDER_EMAIL, recipient_email, text)
        
        return True
        
    except Exception as e:
        print(f"Error sharing property results: {e}")
        # You might want to log this error or show it to the user
        return False