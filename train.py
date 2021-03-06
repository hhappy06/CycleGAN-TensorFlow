import tensorflow as tf
from model import CycleGAN
from reader import Reader
from datetime import datetime
import os
import logging

FLAGS = tf.flags.FLAGS

tf.flags.DEFINE_integer('batch_size', 1, 'batch size, default: 1')
tf.flags.DEFINE_integer('image_size', 128, 'image size, default: 128')
tf.flags.DEFINE_bool('use_lsgan', True,
                     'use lsgan (mean squared error) or cross entropy loss, default: True')
tf.flags.DEFINE_integer('lambda1', 10.0,
                        'weight for forward cycle loss (X->Y->X), default: 10.0')
tf.flags.DEFINE_integer('lambda2', 10.0,
                        'weight for backward cycle loss (Y->X->Y), default: 10.0')
tf.flags.DEFINE_float('learning_rate', 2e-4,
                      'initial learning rate for Adam, default: 0.0002')
tf.flags.DEFINE_float('beta1', 0.5,
                      'momentum term of Adam, default: 0.5')

tf.flags.DEFINE_string('X_train_file', 'data/tfrecords/apple.tfrecords',
                       'X tfrecords file for training, default: data/tfrecords/apple.tfrecords')
tf.flags.DEFINE_string('Y_train_file', 'data/tfrecords/orange.tfrecords',
                       'Y tfrecords file for training, default: data/tfrecords/orange.tfrecords')


def train():
  current_time = datetime.now().strftime("%Y%m%d-%H%M")
  checkpoints_dir = "checkpoints/{}".format(current_time)
  os.makedirs(checkpoints_dir, exist_ok=True)

  graph = tf.Graph()
  with graph.as_default():
    cycle_gan = CycleGAN(
        batch_size=FLAGS.batch_size,
        image_size=FLAGS.image_size,
        use_lsgan=FLAGS.use_lsgan,
        lambda1=FLAGS.lambda1,
        lambda2=FLAGS.lambda1,
        learning_rate=FLAGS.learning_rate,
        beta1=FLAGS.beta1,
        X_train_file=FLAGS.X_train_file,
        Y_train_file=FLAGS.Y_train_file
    )
    G_loss, D_Y_loss, F_loss, D_X_loss = cycle_gan.model()
    optimizers = cycle_gan.optimize(G_loss, D_Y_loss, F_loss, D_X_loss)
    train_writer = tf.summary.FileWriter(checkpoints_dir, graph)

  with tf.Session(graph=graph) as sess:
    sess.run(tf.global_variables_initializer())

    coord = tf.train.Coordinator()
    threads = tf.train.start_queue_runners(sess=sess, coord=coord)

    try:
      step = 0
      while not coord.should_stop():
        _, G_loss_val, D_Y_loss_val, F_loss_val, D_X_loss_val, summary = (
              sess.run(
                  [optimizers, G_loss, D_Y_loss, F_loss, D_X_loss, cycle_gan.summary]
              )
        )

        train_writer.add_summary(summary, step)
        train_writer.flush()

        if step % 100 == 0:
          logging.info('-----------Step %d:-------------' % step)
          logging.info('  G_loss   : {}'.format(G_loss_val))
          logging.info('  D_Y_loss : {}'.format(D_Y_loss_val))
          logging.info('  F_loss   : {}'.format(F_loss_val))
          logging.info('  D_X_loss : {}'.format(D_X_loss_val))

        if step % 1000 == 0:
          save_path = cycle_gan.saver.save(sess, checkpoints_dir + "/model.ckpt", global_step=step)
          logging.info("Model saved in file: %s" % save_path)

        step += 1

    except KeyboardInterrupt:
      logging.info('Interrupted')
      coord.request_stop()
    except Exception as e:
      coord.request_stop(e)
    finally:
      save_path = cycle_gan.saver.save(sess, checkpoints_dir + "/model.ckpt", global_step=step)
      logging.info("Model saved in file: %s" % save_path)
      # When done, ask the threads to stop.
      coord.request_stop()
      coord.join(threads)

def main(unused_argv):
  train()

if __name__ == '__main__':
  logging.basicConfig(level=logging.INFO)
  tf.app.run()
