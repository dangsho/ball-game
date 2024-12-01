const config = {
    type: Phaser.AUTO,
    width: 800,
    height: 600,
    physics: {
        default: 'arcade',
        arcade: {
            gravity: { y: 200 },
            debug: false
        }
    },
    scene: {
        preload: preload,
        create: create,
        update: update
    }
};

let ball;

const game = new Phaser.Game(config);

function preload() {
    this.load.image('ball', 'ball.png');  // تصویر توپ را بارگذاری می‌کند
}

function create() {
    ball = this.physics.add.image(400, 300, 'ball');  // توپ را در مرکز صفحه قرار می‌دهد
    ball.setBounce(1);  // خاصیت جهش به توپ می‌دهد
    ball.setCollideWorldBounds(true);  // توپ را در مرزهای صفحه نگه می‌دارد

    // اضافه کردن کنترل به توپ
    this.input.on('pointerdown', () => {
        ball.setVelocity(Phaser.Math.Between(-200, 200), -300);  // هنگام کلیک، توپ به حرکت در می‌آید
    });
}

function update() {
    // منطق اضافه برای بازی می‌تواند اینجا نوشته شود
}
