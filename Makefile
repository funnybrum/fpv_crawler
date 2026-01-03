REPO_DIR := $(shell pwd)

.PHONY: install install-services

install: service-user
	@echo "✅ User-level installation complete. No sudo required for control!"

install-services:
    VIDEO_SERVICE := crawler-video.service
    MAIN_SERVICE := crawler-main.service
    USER_SYSTEMD_DIR := $(HOME)/.config/systemd/user

    # Add the services
    @echo "🔗 Linking and configuring services..."
	mkdir -p $(USER_SYSTEMD_DIR)

	# Link the main and the video service.
	ln -sf $(REPO_DIR)/deploy/$(VIDEO_SERVICE) $(USER_SYSTEMD_DIR)/$(VIDEO_SERVICE)
	ln -sf $(REPO_DIR)/deploy/$(MAIN_SERVICE) $(USER_SYSTEMD_DIR)/$(MAIN_SERVICE)

	# Refresh daemon
	systemctl --user daemon-reload

	# Automatically start the MAIN service
	systemctl --user enable $(MAIN_SERVICE)
	@echo "✅ Services configured."

    # Enable starting and stopping the service without sudo
	@echo "⏳ Enabling lingering for user $(USER)..."
	sudo loginctl enable-linger $(USER)
