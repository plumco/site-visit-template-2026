# ==========================================
# TAB 3: EXECUTIVE SUMMARY (TABLE GENERATOR)
# ==========================================
with tab_exec:
    # 1. Ensure Date is formatted for the month filter globally
    if 'Month' not in visits_df.columns and not visits_df.empty:
        visits_df['Month'] = pd.to_datetime(visits_df['Date of Visit'], errors='coerce').dt.strftime('%b %Y')
        visits_df['Month'] = visits_df['Month'].fillna('Unknown')

    # 2. Create Header and Dropdown in the same row
    exec_col1, exec_col2 = st.columns([4, 1])
    with exec_col1:
        st.subheader("Monthly Summary (Associate Data)")
    with exec_col2:
        if not visits_df.empty:
            exec_months = ['All'] + list(visits_df['Month'].dropna().unique())
            selected_month = st.selectbox("Month Filter", exec_months, label_visibility="collapsed")
        else:
            selected_month = 'All'

    if visits_df.empty:
        st.warning("No Visit Log data found to build the summary.")
    else:
        # 3. Filter Data based on Dropdown
        exec_filtered_df = visits_df.copy()
        if selected_month != 'All':
            exec_filtered_df = exec_filtered_df[exec_filtered_df['Month'] == selected_month]

        if exec_filtered_df.empty:
            st.info(f"No records found for {selected_month}.")
        else:
            # Pre-process status logic so we can check for 'Pending'
            if 'Status' not in exec_filtered_df.columns:
                exec_filtered_df['Status'] = exec_filtered_df.apply(get_visit_status, axis=1)

            # Ensure FloorsVisited is numeric for summing
            floors_col = 'FloorsVisited' if 'FloorsVisited' in exec_filtered_df.columns else 'Floors Visited'
            exec_filtered_df['Num_Floors'] = pd.to_numeric(exec_filtered_df.get(floors_col, []), errors='coerce').fillna(0)
            
            # Clean the "Is Report Visit?" column for accurate checking
            exec_filtered_df['Clean_Report_Mark'] = exec_filtered_df.get('Is Report Visit?', '').astype(str).str.strip().str.upper()
            
            # Generate the Grouped Summary Table
            summary_rows = []
            
            # Group by Associate ID using the FILTERED dataframe
            for assoc, group in exec_filtered_df.groupby('Associate ID'):
                if pd.isna(assoc) or str(assoc).strip() == '':
                    continue
                    
                # 1. Floor Visit (Sum of FloorsVisited)
                floor_visit_sum = group['Num_Floors'].sum()
                
                # 2. Site Tower Visit (Count of Site Names)
                site_tower_count = group['Site Name'].count() if 'Site Name' in group.columns else 0
                
                # 3. Report Mark (YES) -> count
                report_yes_count = len(group[group['Clean_Report_Mark'].isin(['YES', 'Y', 'TRUE'])])
                
                # 4. Suggestion Visit (NO) -> count
                report_no_count = len(group[group['Clean_Report_Mark'].isin(['NO', 'N', 'FALSE'])])
                
                # 5. Report Pending (From Status calculation)
                report_pending = len(group[group['Status'] == 'Pending'])
                
                # 6. Report sent to the client (Is report visit? YES and sum FloorsVisited)
                client_sent_floors = group[group['Clean_Report_Mark'].isin(['YES', 'Y', 'TRUE'])]['Num_Floors'].sum()
                
                # Append Row exactly matching the requested format
                summary_rows.append({
                    'Associate ID': assoc,
                    'Floor Visit': int(floor_visit_sum),
                    'Site Tower visit': int(site_tower_count),
                    'Repoert Mark (YES)': report_yes_count,
                    'Suggestion Visit (NO)': report_no_count,
                    'Report Pending': report_pending,
                    'Repoert send to the client': int(client_sent_floors),
                    'March Month(Pending) Repoert send to the client': 0, # Placeholder for previous month
                    'report total with Pend': int(client_sent_floors)     # Summing current + previous
                })
                
            summary_df = pd.DataFrame(summary_rows)
            
            # Display the stylized dataframe
            st.dataframe(
                summary_df, 
                use_container_width=True, 
                hide_index=True,
                column_config={
                    "Repoert send to the client": st.column_config.NumberColumn(
                        "Repoert send to the client",
                        help="Sum of floors where Is Report Visit is YES"
                    )
                }
            )
