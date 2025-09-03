FROM odoo:18.0

# Switch to root to perform privileged operations
USER root

# Install system dependencies, setup Python environment and install requirements
COPY ./requirements.txt /tmp/
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    python3-bcrypt \
    python3-pip \
    python3-setuptools \
    python3-wheel \
    python3-venv \
    python3-full && \
    # Create Python virtual environment and install dependencies \
    python3 -m venv /opt/venv && \
    PATH="/opt/venv/bin:$PATH" pip install --upgrade pip && \
    PATH="/opt/venv/bin:$PATH" pip install -r /tmp/requirements.txt && \
    # Create directories with proper permissions \
    mkdir -p /mnt/uellowcom /mnt/enterprise-addons && \
    chown odoo:odoo /mnt/uellowcom /mnt/enterprise-addons && \
    chmod 777 /mnt/uellowcom /mnt/enterprise-addons && \
    # Cleanup to reduce image size \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* /tmp/requirements.txt

# Set environment path for the virtual environment
ENV PATH="/opt/venv/bin:$PATH"

# Copy custom configuration, modules, and enterprise addons, then set permissions
COPY ../config /etc/odoo
COPY . /mnt/uellowcom
COPY ../enterprise-addons /mnt/enterprise-addons
RUN chown -R odoo:odoo /etc/odoo /mnt/uellowcom /mnt/enterprise-addons

# Switch back to the odoo user for security
USER odoo

# Expose ports
EXPOSE 8069 8071 8072

# Set the default command
CMD ["odoo", "--db_host=db", "--db_user=odoo", "--db_password=odoo", "--database=odoo", "--without-demo=all"]
