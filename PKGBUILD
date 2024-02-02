pkgname=kvmd-oled
pkgver=0.26
pkgrel=1
pkgdesc="PiKVM - A small OLED daemon"
url="https://github.com/pikvm/packages"
license=(GPL)
arch=(any)
depends=(
	python-luma-oled
	python-netifaces
	python-psutil
	python-pyusb
	python-pillow
	ttf-proggy-clean
)
source=(
	$pkgname.service
	$pkgname-shutdown.service
	$pkgname-reboot.service
	$pkgname.py
	hello.ppm
	pikvm.ppm
)
md5sums=(SKIP SKIP SKIP SKIP SKIP SKIP)


package() {
	mkdir -p "$pkgdir/usr/bin"
	install -Dm755 $pkgname.py "$pkgdir/usr/bin/$pkgname"

	mkdir -p "$pkgdir/usr/lib/systemd/system"
	cp *.service "$pkgdir/usr/lib/systemd/system"

	mkdir -p "$pkgdir/usr/share/kvmd-oled"
	cp *.ppm "$pkgdir/usr/share/kvmd-oled"
}
