#include <cstdint>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <map>
#include <set>
#include <sstream>
#include <stdexcept>
#include <string>
#include <string_view>
#include <vector>

#include "lvgl.h"
#include "wyss/adapters/lvgl_panel_view.hpp"
#include "wyss/application/panel_service.hpp"
#include "wyss/ui/design_tokens.hpp"

namespace {
namespace fs = std::filesystem;

using wyss::ui::ManualPage;
using wyss::ui::ShellMode;

struct Framebuffer {
    std::vector<lv_color_t> pixels{static_cast<std::size_t>(wyss::ui::tokens::screen_width) *
                                   static_cast<std::size_t>(wyss::ui::tokens::screen_height)};
};

class Clock final : public wyss::ports::Clock {
   public:
    [[nodiscard]] std::uint64_t now_ms() const noexcept override { return now_; }

   private:
    std::uint64_t now_{1'000};
};

class Commands final : public wyss::ports::CommandPort {
   public:
    bool send_fast(const wyss::domain::FastCommand&) override { return true; }
    bool send_intent(const wyss::domain::Intent&) override { return true; }
    bool confirm(std::string_view, bool, wyss::domain::RiskLevel) override { return true; }
};

void flush(lv_disp_drv_t* driver, const lv_area_t* area, lv_color_t* colors) {
    auto& framebuffer = *static_cast<Framebuffer*>(driver->user_data);
    const int width = wyss::ui::tokens::screen_width;
    std::size_t source = 0;
    for (int y = area->y1; y <= area->y2; ++y) {
        for (int x = area->x1; x <= area->x2; ++x) {
            framebuffer.pixels[static_cast<std::size_t>(y * width + x)] = colors[source++];
        }
    }
    lv_disp_flush_ready(driver);
}

std::vector<std::uint8_t> rgb_bytes(const Framebuffer& framebuffer) {
    std::vector<std::uint8_t> bytes;
    bytes.reserve(framebuffer.pixels.size() * 3);
    for (const auto pixel : framebuffer.pixels) {
        const std::uint16_t value = pixel.full;
        bytes.push_back(static_cast<std::uint8_t>(((value >> 11U) & 0x1FU) * 255U / 31U));
        bytes.push_back(static_cast<std::uint8_t>(((value >> 5U) & 0x3FU) * 255U / 63U));
        bytes.push_back(static_cast<std::uint8_t>((value & 0x1FU) * 255U / 31U));
    }
    return bytes;
}

std::uint64_t fnv1a(const std::vector<std::uint8_t>& bytes) {
    std::uint64_t hash = 14695981039346656037ULL;
    for (const auto byte : bytes) {
        hash ^= byte;
        hash *= 1099511628211ULL;
    }
    return hash;
}

std::string hex_hash(std::uint64_t value) {
    std::ostringstream output;
    output << std::hex << std::setfill('0') << std::setw(16) << value;
    return output.str();
}

void write_ppm(const fs::path& path, const std::vector<std::uint8_t>& bytes) {
    std::ofstream output(path, std::ios::binary);
    if (!output) {
        throw std::runtime_error("no se pudo crear " + path.string());
    }
    output << "P6\n"
           << wyss::ui::tokens::screen_width << ' ' << wyss::ui::tokens::screen_height << "\n255\n";
    output.write(reinterpret_cast<const char*>(bytes.data()),
                 static_cast<std::streamsize>(bytes.size()));
}

std::map<std::string, std::string> read_manifest(const fs::path& path) {
    std::ifstream input(path);
    if (!input) {
        throw std::runtime_error("no se pudo leer el manifiesto " + path.string());
    }
    std::map<std::string, std::string> hashes;
    std::string line;
    while (std::getline(input, line)) {
        if (line.empty() || line.front() == '#') {
            continue;
        }
        std::istringstream fields(line);
        std::string name;
        std::string hash;
        fields >> name >> hash;
        if (name.empty() || hash.empty()) {
            throw std::runtime_error("línea inválida en " + path.string());
        }
        hashes.emplace(std::move(name), std::move(hash));
    }
    return hashes;
}

class Recorder {
   public:
    Recorder(Framebuffer& framebuffer, lv_disp_t* display, fs::path output_dir,
             std::map<std::string, std::string> expected)
        : framebuffer_(framebuffer),
          display_(display),
          output_dir_(std::move(output_dir)),
          expected_(std::move(expected)) {
        fs::create_directories(output_dir_);
    }

    void capture(std::string name) {
        lv_obj_invalidate(lv_scr_act());
        lv_refr_now(display_);
        const auto bytes = rgb_bytes(framebuffer_);
        const auto hash = hex_hash(fnv1a(bytes));
        write_ppm(output_dir_ / (name + ".ppm"), bytes);
        std::cout << name << ' ' << hash << '\n';
        if (!expected_.empty()) {
            const auto found = expected_.find(name);
            if (found == expected_.end()) {
                throw std::runtime_error("falta el escenario " + name + " en el manifiesto");
            }
            if (found->second != hash) {
                throw std::runtime_error("regresión visual en " + name + ": esperado " +
                                         found->second + ", actual " + hash);
            }
            verified_.emplace(std::move(name));
        }
    }

    void finish() const {
        if (!expected_.empty() && verified_.size() != expected_.size()) {
            throw std::runtime_error(
                "el manifiesto contiene escenarios que no fueron renderizados");
        }
        lv_mem_monitor_t memory{};
        lv_mem_monitor(&memory);
        if (memory.free_size < 4'096U) {
            throw std::runtime_error("LVGL terminó con menos de 4 KiB libres");
        }
        std::cout << "lvgl_free_bytes " << memory.free_size << '\n';
    }

   private:
    Framebuffer& framebuffer_;
    lv_disp_t* display_;
    fs::path output_dir_;
    std::map<std::string, std::string> expected_;
    std::set<std::string> verified_;
};

}  // namespace

int main(int argc, char** argv) {
    try {
        fs::path output_dir = ".cache/ui-snapshots";
        fs::path manifest;
        for (int index = 1; index < argc; ++index) {
            const std::string_view argument = argv[index];
            if (argument == "--output-dir" && index + 1 < argc) {
                output_dir = argv[++index];
            } else if (argument == "--verify" && index + 1 < argc) {
                manifest = argv[++index];
            } else {
                throw std::runtime_error("uso: ui_simulator [--output-dir DIR] [--verify FILE]");
            }
        }

        lv_init();
        Framebuffer framebuffer;
        std::vector<lv_color_t> draw_pixels(
            static_cast<std::size_t>(wyss::ui::tokens::screen_width) * 32U);
        lv_disp_draw_buf_t draw_buffer{};
        lv_disp_draw_buf_init(&draw_buffer, draw_pixels.data(), nullptr, draw_pixels.size());
        lv_disp_drv_t driver{};
        lv_disp_drv_init(&driver);
        driver.hor_res = wyss::ui::tokens::screen_width;
        driver.ver_res = wyss::ui::tokens::screen_height;
        driver.draw_buf = &draw_buffer;
        driver.flush_cb = flush;
        driver.user_data = &framebuffer;
        lv_disp_t* display = lv_disp_drv_register(&driver);

        Clock clock;
        Commands commands;
        wyss::adapters::LvglPanelView view;
        wyss::application::PanelService service(clock, commands, view);
        view.begin(service, "light.living");
        view.show_page(static_cast<ManualPage>(255));
        if (view.page() != ManualPage::Inicio) {
            throw std::runtime_error("una pagina manual invalida no volvio a Inicio");
        }

        Recorder recorder(
            framebuffer, display, output_dir,
            manifest.empty() ? std::map<std::string, std::string>{} : read_manifest(manifest));
        recorder.capture("inicio_offline");

        service.set_connection(wyss::domain::ConnectionState::Online);
        service.replace_devices({{"light.living", "Living", true, true, 68, std::nullopt, 4}});
        recorder.capture("inicio_online");

        view.show_page(ManualPage::Hogar);
        recorder.capture("hogar");
        view.show_page(ManualPage::Media);
        recorder.capture("media");
        view.show_page(ManualPage::Agenda);
        recorder.capture("agenda");
        view.show_page(ManualPage::Sistema);
        recorder.capture("sistema");

        view.set_mode(ShellMode::Sleeping);
        recorder.capture("reposo");

        view.set_mode(ShellMode::Conversation);
        view.render_execution({"req-visual", wyss::domain::ExecutionState::Planning,
                               "Analizando un pedido deliberadamente largo para comprobar el "
                               "ajuste de texto sin ocultar los controles principales.",
                               81});
        recorder.capture("conversacion");

        view.render_plan({"plan-visual",
                          "Preparar el living para una película sin tocar cerraduras",
                          wyss::domain::RiskLevel::B,
                          {{"Atenuar la luz principal al treinta por ciento", "light.living"},
                           {"Encender la luz ambiental azul", "light.ambient"},
                           {"Iniciar el modo no molestar", "scene.cinema"}},
                          90'000});
        recorder.capture("confirmacion");
        recorder.finish();
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "ui_simulator: " << error.what() << '\n';
        return 1;
    }
}
