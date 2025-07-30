import streamlit as st
import json
import re
from datetime import datetime
import zipfile
from io import BytesIO

st.set_page_config(
    page_title="Smart Close.com Doc Splitter",
    page_icon="✂️",
    layout="wide"
)

def estimate_tokens(text):
    """Rough estimate of tokens (1 token ≈ 4 characters)"""
    return len(text) // 4

def split_by_priority(scraped_content, max_tokens_per_file=50000):
    """Split documentation by priority and use case"""
    
    # Define priority categories based on your real estate workflow
    priority_splits = {
        'Core_API_Essentials': {
            'description': 'Essential API concepts you\'ll use daily',
            'keywords': ['introduction', 'authentication', 'getting-started', 'api-clients', 'rate-limits', 'errors'],
            'max_tokens': 30000,
            'content': []
        },
        'Leads_Management': {
            'description': 'Everything about leads - your primary object type',
            'keywords': ['leads', 'lead', 'contacts', 'contact'],
            'max_tokens': 40000,
            'content': []
        },
        'Opportunities_Pipeline': {
            'description': 'Opportunities and sales pipeline management',
            'keywords': ['opportunities', 'opportunity', 'pipeline', 'deals', 'sales'],
            'max_tokens': 35000,
            'content': []
        },
        'Activities_Communication': {
            'description': 'Calls, emails, notes, and communication tracking',
            'keywords': ['activities', 'activity', 'calls', 'emails', 'notes', 'communication', 'sms'],
            'max_tokens': 35000,
            'content': []
        },
        'Custom_Fields_Objects': {
            'description': 'Custom fields and objects for your specific workflow',
            'keywords': ['custom-fields', 'custom-objects', 'custom-activities', 'schemas'],
            'max_tokens': 30000,
            'content': []
        },
        'Automation_Webhooks': {
            'description': 'Webhooks and automation for streamlined workflows',
            'keywords': ['webhooks', 'webhook', 'automation', 'integrations', 'zapier'],
            'max_tokens': 25000,
            'content': []
        },
        'Reporting_Analytics': {
            'description': 'Reporting and analytics for business insights',
            'keywords': ['reporting', 'reports', 'analytics', 'metrics', 'dashboard'],
            'max_tokens': 25000,
            'content': []
        },
        'Advanced_Features': {
            'description': 'Advanced features and specialized functionality',
            'keywords': ['bulk', 'import', 'export', 'scheduling', 'templates', 'sequences'],
            'max_tokens': 30000,
            'content': []
        }
    }
    
    # Categorize content
    uncategorized = []
    
    for url, content in scraped_content.items():
        categorized = False
        url_lower = url.lower()
        title_lower = content['title'].lower()
        content_lower = content['content'].lower()
        
        for category, config in priority_splits.items():
            if any(keyword in url_lower or keyword in title_lower or keyword in content_lower 
                   for keyword in config['keywords']):
                config['content'].append(content)
                categorized = True
                break
        
        if not categorized:
            uncategorized.append(content)
    
    # Create files with token limits
    final_files = {}
    
    for category, config in priority_splits.items():
        if config['content']:
            # Sort by relevance (title matches get priority)
            config['content'].sort(key=lambda x: (
                -sum(1 for keyword in config['keywords'] if keyword in x['title'].lower()),
                -sum(1 for keyword in config['keywords'] if keyword in x['url'].lower())
            ))
            
            current_tokens = 0
            included_content = []
            
            for content in config['content']:
                content_tokens = estimate_tokens(content['content'])
                if current_tokens + content_tokens <= config['max_tokens']:
                    included_content.append(content)
                    current_tokens += content_tokens
                else:
                    # If single item is too large, truncate it
                    if not included_content and content_tokens > config['max_tokens']:
                        truncated_content = content.copy()
                        # Truncate to fit
                        char_limit = config['max_tokens'] * 4 - 1000  # Leave room for headers
                        truncated_content['content'] = content['content'][:char_limit] + "\n\n[Content truncated for size limits]"
                        included_content.append(truncated_content)
                        current_tokens = config['max_tokens']
                    break
            
            if included_content:
                filename = f"Tech_Close_{category}.md"
                file_content = create_focused_file(category, config['description'], included_content)
                final_files[filename] = file_content
    
    # Handle uncategorized content in smaller chunks
    if uncategorized:
        chunk_size = 20000  # Smaller chunks for misc content
        for i, chunk_start in enumerate(range(0, len(uncategorized), 10)):  # 10 items per chunk max
            chunk_content = uncategorized[chunk_start:chunk_start + 10]
            
            # Check token limit
            current_tokens = 0
            final_chunk = []
            
            for content in chunk_content:
                content_tokens = estimate_tokens(content['content'])
                if current_tokens + content_tokens <= chunk_size:
                    final_chunk.append(content)
                    current_tokens += content_tokens
                else:
                    break
            
            if final_chunk:
                filename = f"Tech_Close_Additional_Part{i+1}.md"
                file_content = create_focused_file(
                    f"Additional_Part{i+1}", 
                    f"Additional Close.com documentation (Part {i+1})", 
                    final_chunk
                )
                final_files[filename] = file_content
    
    return final_files

def create_focused_file(category, description, content_list):
    """Create a focused documentation file"""
    file_content = f"# Close.com {category.replace('_', ' ')} Documentation\n\n"
    file_content += f"**Purpose:** {description}\n\n"
    file_content += f"**Content:** {len(content_list)} pages\n\n"
    file_content += f"**Estimated Tokens:** ~{sum(estimate_tokens(content['content']) for content in content_list):,}\n\n"
    file_content += f"**Last Updated:** {datetime.now().strftime('%B %d, %Y')}\n\n"
    file_content += f"**File Size:** Optimized for AI context windows\n\n"
    file_content += "---\n\n"
    
    # Add quick reference index
    file_content += "## Quick Reference Index\n\n"
    for content in content_list:
        file_content += f"- **{content['title']}** - {content['url']}\n"
    file_content += "\n---\n\n"
    
    # Add full content
    file_content += "## Complete Documentation\n\n"
    
    for content in content_list:
        file_content += f"### {content['title']}\n\n"
        file_content += f"**URL:** {content['url']}\n\n"
        file_content += f"{content['content']}\n\n"
        
        if content['code_examples']:
            file_content += "#### Code Examples\n\n"
            for code in content['code_examples']:
                file_content += f"```{code.get('language', '')}\n"
                file_content += f"{code['content']}\n"
                file_content += "```\n\n"
        
        file_content += "---\n\n"
    
    return file_content

def create_master_strategy_guide(final_files):
    """Create a strategy guide for which files to use when"""
    guide_content = """# Close.com Documentation Strategy Guide

**Purpose:** Guide for which documentation files to use for different AI tasks

**Last Updated:** {date}

---

## 📋 File Usage Strategy

### For Daily CRM Operations:
- **Tech_Close_Core_API_Essentials.md** - Start here for any API work
- **Tech_Close_Leads_Management.md** - For lead-related tasks and automation

### For Sales Pipeline Work:
- **Tech_Close_Opportunities_Pipeline.md** - Deal management and sales workflows
- **Tech_Close_Activities_Communication.md** - Call tracking, email automation

### For Custom Solutions:
- **Tech_Close_Custom_Fields_Objects.md** - Building custom workflows
- **Tech_Close_Automation_Webhooks.md** - Setting up automated processes

### For Analytics & Reporting:
- **Tech_Close_Reporting_Analytics.md** - Business intelligence and metrics

### For Advanced Projects:
- **Tech_Close_Advanced_Features.md** - Complex integrations and features

---

## 🎯 AI Prompting Strategy

### When asking Claude/ChatGPT about Close.com:

**For Basic Questions:** Upload Core_API_Essentials + relevant topic file

**For Custom Development:** Upload Core_API_Essentials + Custom_Fields_Objects + specific feature file

**For Automation Projects:** Upload Core_API_Essentials + Automation_Webhooks + relevant workflow file

**For Reporting/Analytics:** Upload Core_API_Essentials + Reporting_Analytics

---

## 📊 File Statistics

{file_stats}

---

## 💡 Tips for Maximum AI Effectiveness

1. **Start Small:** Always include Core_API_Essentials as your base
2. **Stay Focused:** Only upload files relevant to your current task
3. **Combine Strategically:** Usually 2-3 files max for best results
4. **Update Regularly:** Re-run the scraper monthly to keep docs current

---

## 🔄 When to Use Which Combination

**Building a new integration?**
→ Core_API_Essentials + Leads_Management + Automation_Webhooks

**Improving sales process?**
→ Core_API_Essentials + Opportunities_Pipeline + Activities_Communication

**Custom field setup?**
→ Core_API_Essentials + Custom_Fields_Objects

**Reporting dashboard?**
→ Core_API_Essentials + Reporting_Analytics

**Troubleshooting API issues?**
→ Core_API_Essentials + specific feature file

""".format(
        date=datetime.now().strftime('%B %d, %Y'),
        file_stats="\n".join([f"- **{filename}**: ~{estimate_tokens(content):,} tokens" 
                             for filename, content in final_files.items()])
    )
    
    return guide_content

def main():
    st.title("✂️ Smart Close.com Documentation Splitter")
    st.markdown("### Transform Large Documentation into AI-Optimized Files")
    
    st.markdown("""
    This tool takes your comprehensive Close.com documentation and splits it into 
    **focused, manageable files** that work perfectly with AI context windows.
    """)
    
    # File upload
    st.subheader("📁 Upload Documentation")
    uploaded_file = st.file_uploader(
        "Upload your complete_documentation.json file",
        type=['json'],
        help="This is the JSON file generated by the Close.com scraper"
    )
    
    if uploaded_file is not None:
        try:
            # Load the JSON data
            scraped_content = json.load(uploaded_file)
            
            st.success(f"✅ Loaded {len(scraped_content)} pages of documentation")
            
            # Show current size analysis
            st.subheader("📊 Size Analysis")
            total_tokens = sum(estimate_tokens(content['content']) for content in scraped_content.values())
            total_chars = sum(len(content['content']) for content in scraped_content.values())
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Total Pages", len(scraped_content))
            with col2:
                st.metric("Estimated Tokens", f"{total_tokens:,}")
            with col3:
                st.metric("Total Size", f"{total_chars / 1024 / 1024:.1f} MB")
            
            # Warning about size
            if total_tokens > 100000:
                st.warning(f"⚠️ Documentation is {total_tokens:,} tokens - too large for most AI context windows!")
                st.info("💡 The splitter will create focused files under 50k tokens each")
            
            # Split button
            if st.button("✂️ Create Smart Documentation Split", type="primary"):
                with st.spinner("Analyzing and splitting documentation..."):
                    final_files = split_by_priority(scraped_content)
                    strategy_guide = create_master_strategy_guide(final_files)
                    final_files["Tech_Close_Strategy_Guide.md"] = strategy_guide
                
                st.success(f"✅ Created {len(final_files)} optimized documentation files!")
                
                # Show results
                st.subheader("📋 Generated Files")
                
                for filename, content in final_files.items():
                    if filename != "Tech_Close_Strategy_Guide.md":
                        tokens = estimate_tokens(content)
                        col1, col2, col3 = st.columns([3, 1, 1])
                        with col1:
                            st.write(f"**{filename}**")
                        with col2:
                            st.write(f"{tokens:,} tokens")
                        with col3:
                            if tokens > 60000:
                                st.write("⚠️ Large")
                            elif tokens > 40000:
                                st.write("⚖️ Medium")
                            else:
                                st.write("✅ Optimal")
                
                # Download section
                st.subheader("📥 Download Optimized Files")
                
                # Create ZIP
                zip_buffer = BytesIO()
                with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                    for filename, content in final_files.items():
                        zip_file.writestr(filename, content)
                zip_buffer.seek(0)
                
                current_time = datetime.now().strftime("%Y%m%d_%H%M%S")
                
                st.download_button(
                    label="📦 Download All Optimized Files (ZIP)",
                    data=zip_buffer.getvalue(),
                    file_name=f"close_docs_optimized_{current_time}.zip",
                    mime="application/zip"
                )
                
                # Individual downloads
                st.subheader("📄 Individual File Downloads")
                
                # Prioritize strategy guide
                if "Tech_Close_Strategy_Guide.md" in final_files:
                    st.download_button(
                        label="🎯 **STRATEGY GUIDE** (Download First!)",
                        data=final_files["Tech_Close_Strategy_Guide.md"],
                        file_name="Tech_Close_Strategy_Guide.md",
                        mime="text/markdown",
                        key="strategy_guide"
                    )
                    st.divider()
                
                # Core files
                st.write("**Essential Files:**")
                essential_files = [f for f in final_files.keys() if any(x in f for x in ['Core_API', 'Leads_Management'])]
                for filename in essential_files:
                    if filename != "Tech_Close_Strategy_Guide.md":
                        st.download_button(
                            label=f"📄 {filename}",
                            data=final_files[filename],
                            file_name=filename,
                            mime="text/markdown",
                            key=f"download_{filename}"
                        )
                
                # Other files
                st.write("**Specialized Files:**")
                other_files = [f for f in final_files.keys() if f not in essential_files and f != "Tech_Close_Strategy_Guide.md"]
                for filename in other_files:
                    st.download_button(
                        label=f"📄 {filename}",
                        data=final_files[filename],
                        file_name=filename,
                        mime="text/markdown",
                        key=f"download_{filename}"
                    )
                
                # Usage instructions
                st.subheader("🎯 How to Use These Files")
                st.markdown("""
                **Step 1:** Download and read the **Strategy Guide** first
                
                **Step 2:** For most tasks, upload 2-3 relevant files to Claude/ChatGPT:
                - Always include `Tech_Close_Core_API_Essentials.md`
                - Add 1-2 specific files based on your task
                
                **Step 3:** Reference the Strategy Guide for optimal file combinations
                
                **Examples:**
                - Building automation? → Core + Automation_Webhooks + Leads_Management
                - Custom reporting? → Core + Reporting_Analytics
                - Sales workflow? → Core + Opportunities_Pipeline + Activities_Communication
                """)
        
        except Exception as e:
            st.error(f"❌ Error processing file: {str(e)}")
            st.info("Make sure you uploaded the complete_documentation.json file from the scraper.")
    
    else:
        st.info("👆 Upload your complete_documentation.json file to start splitting")
        
        st.subheader("ℹ️ How This Works")
        st.markdown("""
        **Problem:** Large documentation files exceed AI context limits
        
        **Solution:** Smart splitting by your real estate workflow needs
        
        **Result:** Focused files that give AI deep knowledge without overwhelming context
        
        **Files Created:**
        - 🎯 **Strategy Guide** - Which files to use when
        - 🔧 **Core API Essentials** - Always include this one
        - 🏠 **Leads Management** - Your primary objects
        - 💰 **Opportunities Pipeline** - Sales workflow
        - 📞 **Activities Communication** - Calls, emails, notes
        - ⚙️ **Custom Fields & Objects** - Customization
        - 🔄 **Automation & Webhooks** - Process automation
        - 📊 **Reporting & Analytics** - Business intelligence
        - 🚀 **Advanced Features** - Complex functionality
        """)

if __name__ == "__main__":
    main()
