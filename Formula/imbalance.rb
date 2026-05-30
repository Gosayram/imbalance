class Imbalance < Formula
  desc "SQLite-first context memory for coding agents"
  homepage "https://github.com/imbalance-ai/imbalance"
  url "https://files.pythonhosted.org/packages/source/i/imbalance/imbalance-0.6.0.tar.gz"
  sha256 "PLACEHOLDER_SHA256"
  license "MIT"

  depends_on "python@3.14"
  depends_on "sqlite"

  def install
    virtualenv_install_with_resources
  end

  test do
    system bin/"imbalance", "--version"
  end
end
